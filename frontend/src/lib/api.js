import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';


class callAPI {
  // Method to make GET requests
  async get(endpoint, params = {}, token = null) {
    try {
      const config = {
        headers: {
          'Content-Type': 'application/json',
        },
      };
      if (token) {
        config.headers['Authorization'] = `Token ${token}`;
      }
      const response = await axios.get(`${API_BASE_URL}${endpoint}`, { params, ...config });
      return response.data;
    } catch (error) {
      console.error('GET request error:', error);
      throw error;
    }
  }

  async uploadFile(endpoint, formData, onUploadProgress = null, token = null) {
    try {
      const config = {
        headers: {
          // Don't set Content-Type - let axios handle it for FormData
        },
        onUploadProgress: onUploadProgress
      };
      
      if (token) {
        config.headers['Authorization'] = `Token ${token}`;
      }
      
      console.log('File upload request to:', `${API_BASE_URL}${endpoint}`, 'with FormData');
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData, config);
      console.log('File upload response:', response);
      return response.data;
    } catch (error) {
      console.error('File upload error:', error);
      throw error;
    }
  }

  // Method to make POST requests
  async post(endpoint, data = {}, token = null) {
    try {
      const config = {
        headers: {
          'Content-Type': 'application/json',
        },
      };
      if (token) {
        config.headers['Authorization'] = `Token ${token}`;
      }
      console.log('POST request to:', `${API_BASE_URL}${endpoint}`, 'with data:', data, 'and config:', config);
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, data, config);
      console.log('POST response:', response);
      return response.data;
    } catch (error) {
      console.error('POST request error:', error);
      throw error;
    }
  }

  // Method to make PUT requests
  async put(endpoint, data = {}, token = null) {
    try {
      const config = {
        headers: {
          'Content-Type': 'application/json',
        },
      };
      if (token) {
        config.headers['Authorization'] = `Token ${token}`;
      }
      const response = await axios.put(`${API_BASE_URL}${endpoint}`, data, config);
      return response.data;
    } catch (error) {
      console.error('PUT request error:', error);
      throw error;
    }
  }

  // Method to make DELETE requests
  async delete(endpoint, token = null) {
    try {
      const config = {};
      if (token) {
        config.headers = {
          'Authorization': `Token ${token}`,
        };
      }
      const response = await axios.delete(`${API_BASE_URL}${endpoint}`, config);
      return response.data;
    } catch (error) {
      console.error('DELETE request error:', error);
      throw error;
    }
  }

  async callAPI(method, endpoint, data = {}, params = {}, token = null, onUploadProgress = null) {
    method = method.toLowerCase();
    token =  token || localStorage.getItem('Token');
    console.log(`Calling API: ${method.toUpperCase()} ${endpoint} with data:`, data, 'params:', params, 'token:', token);
    switch (method) {
      case 'get':
        return this.get(endpoint, params, token);
      case 'post':
        return this.post(endpoint, data, token);
      case 'put':
        return this.put(endpoint, data, token);
      case 'delete':
        return this.delete(endpoint, token);
      case 'upload':
        return this.uploadFile(endpoint, data, onUploadProgress, token);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }
}

// make a single instance of the class
const api = new callAPI();
export default api;