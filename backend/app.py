from flask import Flask, request, jsonify, session
from flask_cors import CORS
import redis
import mysql.connector
import json
from datetime import datetime
import os
from kafka import KafkaProducer, KafkaConsumer
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 세션을 위한 credentials 지원
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # 세션을 위한 시크릿 키

# OpenTelemetry 초기화
def init_telemetry():
    """OpenTelemetry 초기화 및 계측 설정"""
    # Grafana OTLP 엔드포인트 설정
    otlp_endpoint = os.getenv('OTLP_ENDPOINT', 'http://grafana.20.249.154.255.nip.io:4317')
    
    # Tracer 설정
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Span Exporter 설정
    span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    span_processor = BatchSpanProcessor(span_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Metric 설정
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    )
    metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
    
    # Flask 자동 계측
    FlaskInstrumentor().instrument_app(app)
    
    # MySQL 자동 계측
    MySQLInstrumentor().instrument()
    
    # Redis 자동 계측
    RedisInstrumentor().instrument()
    
    # Kafka는 전용 instrumentation이 없으므로 제거
    # KafkaInstrumentor().instrument()
    
    print(f"OpenTelemetry initialized with endpoint: {otlp_endpoint}")
    return tracer

# OpenTelemetry 초기화
tracer = init_telemetry()

# # 스레드 풀 생성
# thread_pool = ThreadPoolExecutor(max_workers=5)

# MariaDB 연결 함수
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'my-mariadb'),
        user=os.getenv('MYSQL_USER', 'testuser'),
        password=os.getenv('MYSQL_PASSWORD'),
        database="testdb",
        connect_timeout=30
    )

# Redis 연결 함수
def get_redis_connection():
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'my-redis-master'),
            port=6379,
            password=os.getenv('REDIS_PASSWORD'),
            decode_responses=True,
            db=0,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        # 연결 테스트
        redis_client.ping()
        return redis_client
    except Exception as e:
        print(f"Redis connection error: {str(e)}")
        return None

# Redis 검색 캐시 함수들
def get_search_cache(query):
    """Redis에서 검색 결과 캐시 가져오기"""
    try:
        redis_client = get_redis_connection()
        if redis_client:
            cache_key = f"search:{query}"
            cached_result = redis_client.get(cache_key)
            if cached_result:
                print(f"Cache hit for query: {query}")
                return json.loads(cached_result)
        return None
    except Exception as e:
        print(f"Redis cache get error: {str(e)}")
        return None

def set_search_cache(query, results, expire_time=300):
    """Redis에 검색 결과 캐시 저장 (기본 5분)"""
    try:
        redis_client = get_redis_connection()
        if redis_client:
            cache_key = f"search:{query}"
            redis_client.setex(cache_key, expire_time, json.dumps(results))
            print(f"Cache set for query: {query}, expire: {expire_time}s")
    except Exception as e:
        print(f"Redis cache set error: {str(e)}")

def clear_search_cache():
    """검색 캐시 전체 삭제"""
    try:
        redis_client = get_redis_connection()
        if redis_client:
            # search: 패턴의 모든 키 삭제
            pattern = "search:*"
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                print(f"Cleared {len(keys)} search cache keys")
    except Exception as e:
        print(f"Redis cache clear error: {str(e)}")

def get_cache_stats():
    """캐시 통계 정보 가져오기"""
    try:
        redis_client = get_redis_connection()
        if redis_client:
            pattern = "search:*"
            keys = redis_client.keys(pattern)
            cache_info = {
                'total_cache_keys': len(keys),
                'cache_pattern': pattern,
                'redis_status': 'connected'
            }
            return cache_info
        else:
            return {'redis_status': 'disconnected'}
    except Exception as e:
        return {'redis_status': 'error', 'error': str(e)}

# Kafka 환경 변수 확인 함수
def check_kafka_env_vars():
    """Kafka 환경 변수 확인 및 경고 출력"""
    kafka_servers = os.getenv('KAFKA_SERVERS', 'NOT_SET')
    kafka_username = os.getenv('KAFKA_USERNAME', 'NOT_SET')
    kafka_password = os.getenv('KAFKA_PASSWORD', 'NOT_SET')
    
    # 환경 변수가 설정되지 않은 경우 경고 출력
    if kafka_servers == 'NOT_SET':
        print("⚠️  WARNING: KAFKA_SERVERS environment variable is not set!")
    if kafka_username == 'NOT_SET':
        print("⚠️  WARNING: KAFKA_USERNAME environment variable is not set!")
    if kafka_password == 'NOT_SET':
        print("⚠️  WARNING: KAFKA_PASSWORD environment variable is not set!")
    
    return kafka_servers, kafka_username, kafka_password

# Kafka Consumer 생성 함수
def create_kafka_consumer(group_id, timeout_ms=10000):
    """Kafka Consumer 생성 (공통 설정)"""
    kafka_servers, kafka_username, kafka_password = check_kafka_env_vars()
    
    if kafka_servers == 'NOT_SET' or kafka_username == 'NOT_SET' or kafka_password == 'NOT_SET':
        print("⚠️  WARNING: Kafka environment variables are not set!")
        return None
    
    return KafkaConsumer(
        'api-logs',
        bootstrap_servers=kafka_servers,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        security_protocol='SASL_PLAINTEXT',
        sasl_mechanism='SCRAM-SHA-512',
        sasl_plain_username=kafka_username,
        sasl_plain_password=kafka_password,
        group_id=group_id,
        auto_offset_reset='earliest',
        consumer_timeout_ms=timeout_ms
    )

# Kafka Producer 설정
def get_kafka_producer():
    try:
        # 환경 변수 확인
        kafka_servers, kafka_username, kafka_password = check_kafka_env_vars()
        
        return KafkaProducer(
            bootstrap_servers=kafka_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            security_protocol='SASL_PLAINTEXT',
            sasl_mechanism='SCRAM-SHA-512',
            sasl_plain_username=kafka_username,
            sasl_plain_password=kafka_password,
            # 연결 안정성을 위한 추가 설정
            request_timeout_ms=30000,
            retries=3,
            acks='all'
        )
    except Exception as e:
        print(f"Kafka producer creation error: {str(e)}")
        return None

# Kafka 연결 테스트 함수
def test_kafka_connection():
    """Kafka 연결 상태 테스트"""
    try:
        producer = get_kafka_producer()
        if producer:
            # 간단한 테스트 메시지 전송
            test_data = {
                'timestamp': datetime.now().isoformat(),
                'test': True,
                'message': 'Kafka connection test'
            }
            producer.send('api-logs', test_data)
            producer.flush()
            producer.close()
            return {'status': 'success', 'message': 'Kafka connection successful'}
        else:
            return {'status': 'error', 'message': 'Failed to create Kafka producer'}
    except Exception as e:
        return {'status': 'error', 'message': f'Kafka connection failed: {str(e)}'}

# 로깅 함수
def log_to_redis(action, details):
    try:
        redis_client = get_redis_connection()
        if redis_client:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'details': details
            }
            redis_client.lpush('api_logs', json.dumps(log_entry))
            redis_client.ltrim('api_logs', 0, 99)  # 최근 100개 로그만 유지
            redis_client.close()
        else:
            print("Redis 연결 불가로 로깅 건너뜀")
    except Exception as e:
        print(f"Redis logging error: {str(e)}")

# API 통계 로깅을 비동기로 처리하는 함수
def async_log_api_stats(endpoint, method, status, user_id):
    def _log():
        try:
            producer = get_kafka_producer()
            if producer:
                log_data = {
                    'timestamp': datetime.now().isoformat(),
                    'endpoint': endpoint,
                    'method': method,
                    'status': status,
                    'user_id': user_id,
                    'message': f"{user_id}가 {method} {endpoint} 호출 ({status})"
                }
                producer.send('api-logs', log_data)
                producer.flush()
                producer.close()
                print(f"Kafka log sent: {endpoint} {method} {status}")
            else:
                print("Kafka producer not available, skipping log")
        except Exception as e:
            print(f"Kafka logging error: {str(e)}")
    
    # 새로운 스레드에서 로깅 실행
    Thread(target=_log).start()

# 로그인 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "로그인이 필요합니다"}), 401
        return f(*args, **kwargs)
    return decorated_function

# MariaDB 엔드포인트
@app.route('/db/message', methods=['POST'])
@login_required
def save_to_db():
    try:
        user_id = session['user_id']
        db = get_db_connection()
        data = request.json
        cursor = db.cursor()
        sql = "INSERT INTO messages (message, created_at) VALUES (%s, %s)"
        cursor.execute(sql, (data['message'], datetime.now()))
        db.commit()
        cursor.close()
        db.close()
        
        # 로깅
        log_to_redis('db_insert', f"Message saved: {data['message'][:30]}...")
        
        async_log_api_stats('/db/message', 'POST', 'success', user_id)
        return jsonify({"status": "success"})
    except Exception as e:
        async_log_api_stats('/db/message', 'POST', 'error', user_id)
        log_to_redis('db_insert_error', str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/db/messages', methods=['GET'])
@login_required
def get_from_db():
    try:
        user_id = session['user_id']
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM messages ORDER BY created_at DESC")
        messages = cursor.fetchall()
        cursor.close()
        db.close()
        
        # 비동기 로깅으로 변경
        async_log_api_stats('/db/messages', 'GET', 'success', user_id)
        
        return jsonify(messages)
    except Exception as e:
        if 'user_id' in session:
            async_log_api_stats('/db/messages', 'GET', 'error', session['user_id'])
        return jsonify({"status": "error", "message": str(e)}), 500

# Redis 로그 조회
@app.route('/logs/redis', methods=['GET'])
def get_redis_logs():
    try:
        redis_client = get_redis_connection()
        if redis_client:
            logs = redis_client.lrange('api_logs', 0, -1)
            redis_client.close()
            return jsonify([json.loads(log) for log in logs])
        else:
            return jsonify({"status": "error", "message": "Redis 연결 불가"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Redis 캐시 관리 엔드포인트들
@app.route('/cache/stats', methods=['GET'])
@login_required
def get_cache_statistics():
    """캐시 통계 정보 조회"""
    try:
        stats = get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cache/clear', methods=['POST'])
@login_required
def clear_cache():
    """검색 캐시 전체 삭제"""
    try:
        clear_search_cache()
        return jsonify({"status": "success", "message": "검색 캐시가 삭제되었습니다"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/cache/search/<query>', methods=['DELETE'])
@login_required
def delete_search_cache(query):
    """특정 검색어의 캐시 삭제"""
    try:
        redis_client = get_redis_connection()
        if redis_client:
            cache_key = f"search:{query}"
            deleted = redis_client.delete(cache_key)
            if deleted:
                return jsonify({"status": "success", "message": f"'{query}' 검색 캐시가 삭제되었습니다"})
            else:
                return jsonify({"status": "info", "message": f"'{query}' 검색 캐시가 존재하지 않습니다"})
        else:
            return jsonify({"status": "error", "message": "Redis 연결 불가"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 회원가입 엔드포인트
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"status": "error", "message": "사용자명과 비밀번호는 필수입니다"}), 400
            
        # 비밀번호 해시화
        hashed_password = generate_password_hash(password)
        
        db = get_db_connection()
        cursor = db.cursor()
        
        # 사용자명 중복 체크
        cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "이미 존재하는 사용자명입니다"}), 400
        
        # 사용자 정보 저장
        sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (username, hashed_password))
        db.commit()
        cursor.close()
        db.close()
        
        return jsonify({"status": "success", "message": "회원가입이 완료되었습니다"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# 로그인 엔드포인트
@app.route('/login', methods=['POST'])
def login():
    with tracer.start_as_current_span("login") as span:
        try:
            data = request.json
            username = data.get('username')
            password = data.get('password')
            
            # Span에 사용자 정보 추가 (민감하지 않은 정보만)
            span.set_attribute("user.username", username)
            span.set_attribute("http.method", "POST")
            span.set_attribute("http.route", "/login")
            
            if not username or not password:
                span.set_attribute("error", True)
                span.set_attribute("error.message", "사용자명과 비밀번호는 필수입니다")
                return jsonify({"status": "error", "message": "사용자명과 비밀번호는 필수입니다"}), 400
            
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            db.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = username  # 세션에 사용자 정보 저장
                
                # Redis 세션 저장 (선택적)
                try:
                    redis_client = get_redis_connection()
                    if redis_client:
                        session_data = {
                            'user_id': username,
                            'login_time': datetime.now().isoformat()
                        }
                        redis_client.set(f"session:{username}", json.dumps(session_data))
                        redis_client.expire(f"session:{username}", 3600)
                        redis_client.close()
                    else:
                        print("Redis 연결 불가로 세션 저장 건너뜀")
                except Exception as redis_error:
                    print(f"Redis session error: {str(redis_error)}")
                    # Redis 오류는 무시하고 계속 진행
                
                span.set_attribute("login.success", True)
                return jsonify({
                    "status": "success", 
                    "message": "로그인 성공",
                    "username": username
                })
            
            span.set_attribute("login.success", False)
            span.set_attribute("error", True)
            span.set_attribute("error.message", "잘못된 인증 정보")
            return jsonify({"status": "error", "message": "잘못된 인증 정보"}), 401
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            print(f"Login error: {str(e)}")  # 서버 로그에 에러 출력
            return jsonify({"status": "error", "message": "로그인 처리 중 오류가 발생했습니다"}), 500

# 로그아웃 엔드포인트
@app.route('/logout', methods=['POST'])
def logout():
    try:
        if 'user_id' in session:
            username = session['user_id']
            
            # Redis 세션 삭제 시도 (Redis 오류는 무시하고 계속 진행)
            try:
                redis_client = get_redis_connection()
                if redis_client:
                    redis_client.delete(f"session:{username}")
                    redis_client.close()
                    print(f"Redis session deleted for user: {username}")
                else:
                    print("Redis 연결 불가로 세션 삭제 건너뜀")
            except Exception as redis_error:
                print(f"Redis session cleanup error (ignored): {str(redis_error)}")
                # Redis 오류는 무시하고 계속 진행
            
            # Flask 세션에서 사용자 정보 제거 (이 부분은 반드시 실행되어야 함)
            session.pop('user_id', None)
            print(f"Flask session cleared for user: {username}")
            
        return jsonify({"status": "success", "message": "로그아웃 성공"})
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        # Redis 오류가 아닌 다른 오류가 발생한 경우에도 사용자에게는 성공 응답
        # (Redis가 없어도 로그아웃은 가능해야 함)
        return jsonify({"status": "success", "message": "로그아웃 완료 (일부 정리 작업 실패)"}), 200

# 메시지 검색 (DB에서 검색)
@app.route('/db/messages/search', methods=['GET'])
@login_required
def search_messages():
    with tracer.start_as_current_span("search_messages") as span:
        try:
            query = request.args.get('q', '')
            user_id = session['user_id']
            
            # Span에 검색 정보 추가
            span.set_attribute("search.query", query)
            span.set_attribute("user.id", user_id)
            span.set_attribute("http.method", "GET")
            span.set_attribute("http.route", "/db/messages/search")
            
            # Redis에서 검색 캐시 확인
            cached_results = get_search_cache(query)
            if cached_results:
                span.set_attribute("cache.hit", True)
                async_log_api_stats('/db/messages/search', 'GET', 'cache_hit', user_id)
                return jsonify(cached_results)

            # DB에서 검색
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            sql = "SELECT * FROM messages WHERE message LIKE %s ORDER BY created_at DESC"
            cursor.execute(sql, (f"%{query}%",))
            results = cursor.fetchall()
            cursor.close()
            db.close()
            
            # Redis에 검색 결과 캐시
            set_search_cache(query, results)

            # 검색 이력을 Kafka에 저장
            async_log_api_stats('/db/messages/search', 'GET', 'success', user_id)
            
            return jsonify(results)
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            if 'user_id' in session:
                async_log_api_stats('/db/messages/search', 'GET', 'error', session['user_id'])
            return jsonify({"status": "error", "message": str(e)}), 500

# Kafka 연결 테스트 엔드포인트
@app.route('/logs/kafka/test', methods=['GET'])
@login_required
def test_kafka_connection_endpoint():
    """Kafka 연결 상태 테스트"""
    try:
        result = test_kafka_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Kafka 로그 조회 엔드포인트 (개선된 버전)
@app.route('/logs/kafka', methods=['GET'])
@login_required
def get_kafka_logs():
    try:
        # 쿼리 파라미터로 필터링
        limit = int(request.args.get('limit', 100))
        endpoint = request.args.get('endpoint')
        status = request.args.get('status')
        user_id = request.args.get('user_id')
        
        # 날짜 필터링
        start_time = None
        end_time = None
        if request.args.get('start_date'):
            start_time = datetime.fromisoformat(request.args.get('start_date'))
        if request.args.get('end_date'):
            end_time = datetime.fromisoformat(request.args.get('end_date'))
        
        logs = get_kafka_logs_with_filter(
            limit=limit,
            endpoint=endpoint,
            status=status,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return jsonify({
            'status': 'success',
            'data': logs,
            'count': len(logs),
            'filters': {
                'endpoint': endpoint,
                'status': status,
                'user_id': user_id,
                'start_date': request.args.get('start_date'),
                'end_date': request.args.get('end_date')
            }
        })
    except Exception as e:
        print(f"Kafka log retrieval error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# API 통계 대시보드
@app.route('/logs/kafka/stats', methods=['GET'])
@login_required
def get_kafka_statistics():
    """API 통계 정보 조회"""
    try:
        stats = get_api_statistics()
        return jsonify({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        print(f"Kafka statistics error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Kafka 로그 검색
@app.route('/logs/kafka/search', methods=['GET'])
@login_required
def search_kafka_logs_endpoint():
    """Kafka 로그 키워드 검색"""
    try:
        query = request.args.get('q', '')
        # 빈 검색어일 때는 전체 로그 반환
        if not query:
            limit = int(request.args.get('limit', 50))
            results = get_kafka_logs_with_filter(limit=limit)
            return jsonify({
                'status': 'success',
                'data': results,
                'count': len(results),
                'query': 'all'
            })
        
        limit = int(request.args.get('limit', 50))
        results = search_kafka_logs(query, limit)
        
        return jsonify({
            'status': 'success',
            'data': results,
            'count': len(results),
            'query': query
        })
    except Exception as e:
        print(f"Kafka log search error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 엔드포인트별 통계
@app.route('/logs/kafka/endpoints', methods=['GET'])
@login_required
def get_endpoint_statistics():
    """엔드포인트별 API 호출 통계"""
    try:
        stats = get_api_statistics()
        endpoint_stats = stats.get('endpoints', {})
        
        # 상위 10개 엔드포인트
        top_endpoints = sorted(endpoint_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'status': 'success',
            'data': {
                'top_endpoints': top_endpoints,
                'total_endpoints': len(endpoint_stats)
            }
        })
    except Exception as e:
        print(f"Endpoint statistics error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 사용자별 활동 통계
@app.route('/logs/kafka/users', methods=['GET'])
@login_required
def get_user_statistics():
    """사용자별 API 호출 통계"""
    try:
        stats = get_api_statistics()
        user_stats = stats.get('users', {})
        
        # 상위 10명 사용자
        top_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return jsonify({
            'status': 'success',
            'data': {
                'top_users': top_users,
                'total_users': len(user_stats)
            }
        })
    except Exception as e:
        print(f"User statistics error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 에러 로그 조회
@app.route('/logs/kafka/errors', methods=['GET'])
@login_required
def get_error_logs():
    """최근 에러 로그 조회"""
    try:
        limit = int(request.args.get('limit', 20))
        logs = get_kafka_logs_with_filter(limit=limit, status='error')
        
        return jsonify({
            'status': 'success',
            'data': logs,
            'count': len(logs)
        })
    except Exception as e:
        print(f"Error logs retrieval error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Kafka 로그 관리 및 통계 함수들
def get_kafka_logs_with_filter(limit=100, endpoint=None, status=None, user_id=None, start_time=None, end_time=None):
    """필터링된 Kafka 로그 조회"""
    try:
        consumer = create_kafka_consumer('api-logs-viewer', 10000)
        if consumer is None:
            return []
        
        logs = []
        try:
            for message in consumer:
                log_data = message.value
                
                # 필터링 적용
                if endpoint and log_data.get('endpoint') != endpoint:
                    continue
                if status and log_data.get('status') != status:
                    continue
                if user_id and log_data.get('user_id') != user_id:
                    continue
                if start_time:
                    log_timestamp = datetime.fromisoformat(log_data.get('timestamp', ''))
                    if log_timestamp < start_time:
                        continue
                if end_time:
                    log_timestamp = datetime.fromisoformat(log_data.get('timestamp', ''))
                    if log_timestamp > end_time:
                        continue
                
                logs.append({
                    'timestamp': log_data.get('timestamp'),
                    'endpoint': log_data.get('endpoint'),
                    'method': log_data.get('method'),
                    'status': log_data.get('status'),
                    'user_id': log_data.get('user_id'),
                    'message': log_data.get('message')
                })
                
                if len(logs) >= limit:
                    break
        finally:
            consumer.close()
        
        # 시간 역순으로 정렬
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        return logs
    except Exception as e:
        print(f"Kafka log retrieval error: {str(e)}")
        return []

def get_api_statistics():
    """API 통계 정보 조회"""
    try:
        consumer = create_kafka_consumer('api-stats-viewer', 5000)
        if consumer is None:
            return {}
        
        stats = {
            'total_calls': 0,
            'endpoints': {},
            'status_codes': {},
            'users': {},
            'recent_errors': []
        }
        
        try:
            for message in consumer:
                log_data = message.value
                stats['total_calls'] += 1
                
                # 엔드포인트별 통계
                endpoint = log_data.get('endpoint', 'unknown')
                stats['endpoints'][endpoint] = stats['endpoints'].get(endpoint, 0) + 1
                
                # 상태 코드별 통계
                status = log_data.get('status', 'unknown')
                stats['status_codes'][status] = stats['status_codes'].get(status, 0) + 1
                
                # 사용자별 통계
                user = log_data.get('user_id', 'anonymous')
                stats['users'][user] = stats['users'].get(user, 0) + 1
                
                # 최근 에러 로그
                if status == 'error' and len(stats['recent_errors']) < 10:
                    stats['recent_errors'].append({
                        'timestamp': log_data.get('timestamp'),
                        'endpoint': endpoint,
                        'message': log_data.get('message')
                    })
        finally:
            consumer.close()
        
        return stats
    except Exception as e:
        print(f"API statistics error: {str(e)}")
        return {}

def search_kafka_logs(query, limit=50):
    """Kafka 로그에서 키워드 검색"""
    try:
        consumer = create_kafka_consumer('api-search-viewer', 8000)
        if consumer is None:
            return []
        
        results = []
        try:
            for message in consumer:
                log_data = message.value
                
                # 키워드 검색
                searchable_text = f"{log_data.get('endpoint', '')} {log_data.get('message', '')} {log_data.get('user_id', '')}"
                if query.lower() in searchable_text.lower():
                    results.append({
                        'timestamp': log_data.get('timestamp'),
                        'endpoint': log_data.get('endpoint'),
                        'method': log_data.get('method'),
                        'status': log_data.get('status'),
                        'user_id': log_data.get('user_id'),
                        'message': log_data.get('message')
                    })
                
                if len(results) >= limit:
                    break
        finally:
            consumer.close()
        
        # 시간 역순으로 정렬
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        return results
    except Exception as e:
        print(f"Kafka log search error: {str(e)}")
        return []

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 