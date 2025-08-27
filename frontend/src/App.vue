<template>
  <div id="app">
    <h1>K8s 마이크로서비스 데모</h1>
    
    <!-- 로그인/회원가입 섹션 -->
    <div class="section" v-if="!isLoggedIn">
      <div v-if="!showRegister">
        <h2>로그인</h2>
        <input v-model="username" placeholder="사용자명">
        <input v-model="password" type="password" placeholder="비밀번호">
        <button @click="login">로그인</button>
        <button @click="showRegister = true" class="register-btn">회원가입</button>
      </div>
      <div v-else>
        <h2>회원가입</h2>
        <input v-model="registerUsername" placeholder="사용자명">
        <input v-model="registerPassword" type="password" placeholder="비밀번호">
        <input v-model="confirmPassword" type="password" placeholder="비밀번호 확인">
        <button @click="register">가입하기</button>
        <button @click="showRegister = false">로그인으로 돌아가기</button>
      </div>
    </div>

    <div v-else>
      <div class="user-info">
        <span>안녕하세요, {{ username }}님</span>
        <button @click="logout">로그아웃</button>
      </div>

      <div class="container">
        <div class="section">
          <h2>MariaDB 메시지 관리</h2>
          <input v-model="dbMessage" placeholder="저장할 메시지 입력">
          <button @click="saveToDb">DB에 저장</button>
          <button @click="getFromDb">DB에서 조회</button>
          <button @click="insertSampleData" class="sample-btn">샘플 데이터 저장</button>
          <div v-if="loading" class="loading-spinner">
            <p>데이터를 불러오는 중...</p>
          </div>
          <div v-if="dbData.length && !loading">
            <h3>저장된 메시지:</h3>
            <ul>
              <li v-for="item in dbData" :key="item.id">{{ item.message }} ({{ formatDate(item.created_at) }})</li>
            </ul>
          </div>
        </div>

        <div class="section">
          <h2>Redis 로그</h2>
          <button @click="getRedisLogs">로그 조회</button>
          <div v-if="redisLogs.length">
            <h3>API 호출 로그:</h3>
            <ul>
              <li v-for="(log, index) in redisLogs" :key="index">
                [{{ formatDate(log.timestamp) }}] {{ log.action }}: {{ log.details }}
              </li>
            </ul>
          </div>
        </div>

        <div class="section">
          <h2>Kafka 로그 모니터링</h2>
          <div class="kafka-controls">
            <button @click="getKafkaLogs">기본 로그 조회</button>
            <button @click="getKafkaStats">통계 대시보드</button>
            <button @click="getErrorLogs">에러 로그</button>
            <button @click="getEndpointStats">엔드포인트 통계</button>
            <button @click="getUserStats">사용자 통계</button>
          </div>
          
          <!-- 로그 필터링 -->
          <div class="log-filters">
            <input v-model="kafkaFilters.endpoint" placeholder="엔드포인트 필터">
            <input v-model="kafkaFilters.status" placeholder="상태 필터">
            <input v-model="kafkaFilters.user_id" placeholder="사용자 ID 필터">
            <input type="date" v-model="kafkaFilters.start_date">
            <input type="date" v-model="kafkaFilters.end_date">
            <button @click="getFilteredKafkaLogs">필터링된 로그 조회</button>
          </div>

          <!-- 로그 검색 -->
          <div class="log-search">
            <input v-model="kafkaSearchQuery" placeholder="로그 검색어 입력">
            <button @click="searchKafkaLogs">검색</button>
          </div>

          <!-- Kafka 로그 결과 -->
          <div v-if="kafkaLogs.length" class="kafka-results">
            <h3>Kafka 로그 ({{ kafkaLogs.length }}개):</h3>
            <table>
              <thead>
                <tr>
                  <th>시간</th>
                  <th>엔드포인트</th>
                  <th>메서드</th>
                  <th>상태</th>
                  <th>사용자</th>
                  <th>메시지</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in kafkaLogs" :key="log.timestamp" :class="{'error-row': log.status === 'error'}">
                  <td>{{ formatDate(log.timestamp) }}</td>
                  <td>{{ log.endpoint }}</td>
                  <td>{{ log.method }}</td>
                  <td :class="'status-' + log.status">{{ log.status }}</td>
                  <td>{{ log.user_id }}</td>
                  <td>{{ log.message }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 통계 대시보드 -->
          <div v-if="kafkaStats.total_calls" class="stats-dashboard">
            <h3>API 통계 대시보드</h3>
            <div class="stats-grid">
              <div class="stat-card">
                <h4>총 API 호출</h4>
                <p class="stat-number">{{ kafkaStats.total_calls }}</p>
              </div>
              <div class="stat-card">
                <h4>엔드포인트 수</h4>
                <p class="stat-number">{{ Object.keys(kafkaStats.endpoints || {}).length }}</p>
              </div>
              <div class="stat-card">
                <h4>사용자 수</h4>
                <p class="stat-number">{{ Object.keys(kafkaStats.users || {}).length }}</p>
              </div>
            </div>
            
            <!-- 상위 엔드포인트 -->
            <div v-if="kafkaStats.endpoints" class="top-endpoints">
              <h4>상위 엔드포인트</h4>
              <ul>
                <li v-for="(endpoint, count) in kafkaStats.endpoints" :key="endpoint">
                  {{ endpoint }}: {{ count }}회
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="section">
          <h2>메시지 검색</h2>
          <div class="search-section">
            <input v-model="searchQuery" placeholder="메시지 검색">
            <button @click="searchMessages">검색</button>
            <button @click="getAllMessages" class="view-all-btn">전체 메시지 보기</button>
          </div>
          <div v-if="searchResults.length > 0" class="search-results">
            <h3>검색 결과:</h3>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>메시지</th>
                  <th>생성 시간</th>
                  <th>사용자</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="result in searchResults" :key="result.id">
                  <td>{{ result.id }}</td>
                  <td>{{ result.message }}</td>
                  <td>{{ formatDate(result.created_at) }}</td>
                  <td>{{ result.user_id || '없음' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

// nginx 프록시를 통해 요청하도록 수정
const API_BASE_URL = '/api';

export default {
  name: 'App',
  data() {
    return {
      username: '',
      password: '',
      isLoggedIn: false,
      searchQuery: '',
      dbMessage: '',
      dbData: [],
      redisLogs: [],
      sampleMessages: [
        '안녕하세요! 테스트 메시지입니다.',
        'K8s 데모 샘플 데이터입니다.',
        '마이크로서비스 테스트 중입니다.',
        '샘플 메시지 입니다.'
      ],
      offset: 0,
      limit: 20,
      loading: false,
      hasMore: true,
      showRegister: false,
      registerUsername: '',
      registerPassword: '',
      confirmPassword: '',
      currentUser: null,
      searchResults: [],
      kafkaLogs: [],
      kafkaStats: {},
      kafkaFilters: {
        endpoint: '',
        status: '',
        user_id: '',
        start_date: '',
        end_date: ''
      },
      kafkaSearchQuery: ''
    }
  },
  methods: {
    // 날짜를 사용자 친화적인 형식으로 변환
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleString();
    },
    
    // MariaDB에 메시지 저장
    async saveToDb() {
      try {
        await axios.post(`${API_BASE_URL}/db/message`, {
          message: this.dbMessage
        });
        this.dbMessage = '';
        this.getFromDb();
        this.getRedisLogs();
      } catch (error) {
        console.error('DB 저장 실패:', error);
      }
    },

    // MariaDB에서 메시지 조회 (페이지네이션 적용)
    async getFromDb() {
      try {
        this.loading = true;
        const response = await axios.get(`${API_BASE_URL}/db/messages?offset=${this.offset}&limit=${this.limit}`);
        this.dbData = response.data;
        this.hasMore = response.data.length === this.limit;
      } catch (error) {
        console.error('DB 조회 실패:', error);
      } finally {
        this.loading = false;
      }
    },

    // 샘플 데이터를 DB에 저장
    async insertSampleData() {
      const randomMessage = this.sampleMessages[Math.floor(Math.random() * this.sampleMessages.length)];
      try {
        await axios.post(`${API_BASE_URL}/db/message`, {
          message: randomMessage
        });
        this.getFromDb();
        this.getRedisLogs();
      } catch (error) {
        console.error('샘플 데이터 저장 실패:', error);
      }
    },

    // Redis에 저장된 API 호출 로그 조회
    async getRedisLogs() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/redis`);
        this.redisLogs = response.data;
      } catch (error) {
        console.error('Redis 로그 조회 실패:', error);
      }
    },

    // Kafka 로그 조회 (기본)
    async getKafkaLogs() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/kafka`);
        this.kafkaLogs = response.data.data || response.data;
      } catch (error) {
        console.error('Kafka 로그 조회 실패:', error);
      }
    },

    // Kafka 통계 대시보드
    async getKafkaStats() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/kafka/stats`);
        this.kafkaStats = response.data.data || response.data;
      } catch (error) {
        console.error('Kafka 통계 조회 실패:', error);
      }
    },

    // Kafka 에러 로그
    async getErrorLogs() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/kafka/errors`);
        this.kafkaLogs = response.data.data || response.data;
      } catch (error) {
        console.error('Kafka 에러 로그 조회 실패:', error);
      }
    },

    // Kafka 엔드포인트 통계
    async getEndpointStats() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/kafka/endpoints`);
        this.kafkaStats.endpoints = response.data.data.endpoints || response.data.endpoints;
      } catch (error) {
        console.error('Kafka 엔드포인트 통계 조회 실패:', error);
      }
    },

    // Kafka 사용자 통계
    async getUserStats() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/kafka/users`);
        this.kafkaStats.users = response.data.data.users || response.data.users;
      } catch (error) {
        console.error('Kafka 사용자 통계 조회 실패:', error);
      }
    },

    // Kafka 필터링된 로그 조회
    async getFilteredKafkaLogs() {
      try {
        const params = {};
        if (this.kafkaFilters.endpoint) params.endpoint = this.kafkaFilters.endpoint;
        if (this.kafkaFilters.status) params.status = this.kafkaFilters.status;
        if (this.kafkaFilters.user_id) params.user_id = this.kafkaFilters.user_id;
        if (this.kafkaFilters.start_date) params.start_date = this.kafkaFilters.start_date;
        if (this.kafkaFilters.end_date) params.end_date = this.kafkaFilters.end_date;
        
        const response = await axios.get(`${API_BASE_URL}/logs/kafka`, { params });
        this.kafkaLogs = response.data.data || response.data;
      } catch (error) {
        console.error('필터링된 Kafka 로그 조회 실패:', error);
      }
    },

    // Kafka 로그 검색
    async searchKafkaLogs() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/kafka/search`, {
          params: { q: this.kafkaSearchQuery }
        });
        this.kafkaLogs = response.data.data || response.data;
      } catch (error) {
        console.error('Kafka 로그 검색 실패:', error);
      }
    },

    // 사용자 로그인 처리
    async login() {
      try {
        const response = await axios.post(`${API_BASE_URL}/login`, {
          username: this.username,
          password: this.password
        });
        
        if (response.data.status === 'success') {
          this.isLoggedIn = true;
          this.currentUser = this.username;
          this.username = '';
          this.password = '';
        } else {
          alert(response.data.message || '로그인에 실패했습니다.');
        }
      } catch (error) {
        console.error('로그인 실패:', error);
        alert(error.response && error.response.data 
          ? error.response.data.message 
          : '로그인에 실패했습니다.');
      }
    },
    
    // 로그아웃 처리
    async logout() {
      try {
        await axios.post(`${API_BASE_URL}/logout`);
        this.isLoggedIn = false;
        this.username = '';
        this.password = '';
      } catch (error) {
        console.error('로그아웃 실패:', error);
      }
    },

    // 메시지 검색 기능
    async searchMessages() {
      try {
        this.loading = true;
        const response = await axios.get(`${API_BASE_URL}/db/messages/search`, {
          params: { q: this.searchQuery }
        });
        this.searchResults = response.data;
      } catch (error) {
        console.error('검색 실패:', error);
        alert('검색에 실패했습니다.');
      } finally {
        this.loading = false;
      }
    },

    // 전체 메시지 조회
    async getAllMessages() {
      try {
        this.loading = true;
        const response = await axios.get(`${API_BASE_URL}/db/messages`);
        this.searchResults = response.data;
      } catch (error) {
        console.error('전체 메시지 로드 실패:', error);
      } finally {
        this.loading = false;
      }
    },

    // 페이지네이션을 위한 추가 데이터 로드
    async loadMore() {
      this.offset += this.limit;
      await this.getFromDb();
    },

    // 회원가입 처리
    async register() {
      if (this.registerPassword !== this.confirmPassword) {
        alert('비밀번호가 일치하지 않습니다');
        return;
      }
      
      try {
        const response = await axios.post(`${API_BASE_URL}/register`, {
          username: this.registerUsername,
          password: this.registerPassword
        });
        
        if (response.data.status === 'success') {
          alert('회원가입이 완료되었습니다. 로그인해주세요.');
          this.showRegister = false;
          this.registerUsername = '';
          this.registerPassword = '';
          this.confirmPassword = '';
        }
      } catch (error) {
        console.error('회원가입 실패:', error);
        alert(error.response && error.response.data && error.response.data.message 
          ? error.response.data.message 
          : '회원가입에 실패했습니다.');
      }
    }
  }
}
</script>

<style>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 5px;
}

input {
  margin-right: 10px;
  padding: 5px;
  width: 300px;
}

button {
  margin-right: 10px;
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}

.sample-btn {
  background-color: #28a745;
}

.sample-btn:hover {
  background-color: #218838;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  margin: 5px 0;
  padding: 5px;
  border-bottom: 1px solid #eee;
}

.pagination {
  text-align: center;
  margin-top: 10px;
}

.pagination button {
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.pagination button:hover {
  background-color: #0056b3;
}

.pagination button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.loading-spinner {
  text-align: center;
  margin-top: 20px;
  font-size: 16px;
  color: #555;
}

.user-info {
  text-align: right;
  padding: 10px;
  margin-bottom: 20px;
}

.search-section {
  margin: 10px 0;
}

.search-section input {
  width: 200px;
  margin-right: 10px;
}

.register-btn {
  background-color: #6c757d;
}

.register-btn:hover {
  background-color: #5a6268;
}

.search-results {
  margin-top: 20px;
}

.search-results table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.search-results th,
.search-results td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.search-results th {
  background-color: #f8f9fa;
  font-weight: bold;
}

.search-results tr:hover {
  background-color: #f5f5f5;
}

.view-all-btn {
  background-color: #6c757d;
}

.view-all-btn:hover {
  background-color: #5a6268;
}

.kafka-controls {
  margin-bottom: 10px;
}

.log-filters {
  margin-bottom: 10px;
}

.log-search {
  margin-bottom: 10px;
}

.kafka-results h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

.kafka-results table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.kafka-results th,
.kafka-results td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.kafka-results th {
  background-color: #f8f9fa;
  font-weight: bold;
}

.kafka-results tr:hover {
  background-color: #f5f5f5;
}

.error-row {
  background-color: #ffebee; /* Red background for error rows */
  color: #d32f2f; /* Darker red text */
}

.status-success {
  color: #28a745; /* Green text for success */
}

.status-error {
  color: #dc3545; /* Red text for error */
}

.status-info {
  color: #17a2b8; /* Blue text for info */
}

.status-warning {
  color: #ffc107; /* Yellow text for warning */
}

.stats-dashboard {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 5px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.stat-card {
  text-align: center;
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 5px;
  background-color: #f9f9f9;
}

.stat-number {
  font-size: 24px;
  font-weight: bold;
  color: #007bff;
}

.top-endpoints {
  margin-top: 15px;
}

.top-endpoints h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.top-endpoints ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.top-endpoints li {
  margin: 5px 0;
  padding: 5px;
  border: 1px solid #eee;
  border-radius: 3px;
  background-color: #f0f0f0;
}
</style> 