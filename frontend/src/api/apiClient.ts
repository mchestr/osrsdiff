import axios, { AxiosInstance } from 'axios';
import * as ApiServices from './index';
import { ApiError } from './core/ApiError';
import { OpenAPI } from './core/OpenAPI';

// Use relative URL when served from same origin, otherwise use env var or localhost
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? '' : 'http://localhost:8000');

// Create axios instance for token refresh
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Configure OpenAPI with base URL and token resolver
OpenAPI.BASE = API_BASE_URL;
OpenAPI.TOKEN = async () => {
  return localStorage.getItem('access_token') || '';
};

// Helper function to handle token refresh and retry
async function handleTokenRefresh<T>(
  apiCall: () => Promise<T>,
  retryCount = 0
): Promise<T> {
  try {
    return await apiCall();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401 && retryCount === 0) {
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        const response = await axiosInstance.post('/auth/refresh', {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);

        // Update OpenAPI token
        OpenAPI.TOKEN = async () => access_token;

        // Retry the original request
        return await handleTokenRefresh(apiCall, retryCount + 1);
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        throw refreshError;
      }
    }
    throw error;
  }
}

// Create wrapper services with token refresh handling
export const api = {
  ...ApiServices,
  AuthenticationService: {
    ...ApiServices.AuthenticationService,
    loginAuthLoginPost: (formData: Parameters<typeof ApiServices.AuthenticationService.loginAuthLoginPost>[0]) =>
      ApiServices.AuthenticationService.loginAuthLoginPost(formData),
    refreshTokenAuthRefreshPost: (requestBody: Parameters<typeof ApiServices.AuthenticationService.refreshTokenAuthRefreshPost>[0]) =>
      ApiServices.AuthenticationService.refreshTokenAuthRefreshPost(requestBody),
    getCurrentUserInfoAuthMeGet: () =>
      handleTokenRefresh(() => ApiServices.AuthenticationService.getCurrentUserInfoAuthMeGet()),
    logoutAuthLogoutPost: () =>
      handleTokenRefresh(() => ApiServices.AuthenticationService.logoutAuthLogoutPost()),
  },
  PlayersService: {
    ...ApiServices.PlayersService,
    addPlayerApiV1PlayersPost: (requestBody: Parameters<typeof ApiServices.PlayersService.addPlayerApiV1PlayersPost>[0]) =>
      handleTokenRefresh(() => ApiServices.PlayersService.addPlayerApiV1PlayersPost(requestBody)),
    listPlayersApiV1PlayersGet: (activeOnly?: boolean) =>
      handleTokenRefresh(() => ApiServices.PlayersService.listPlayersApiV1PlayersGet(activeOnly)),
    removePlayerApiV1PlayersUsernameDelete: (username: string) =>
      handleTokenRefresh(() => ApiServices.PlayersService.removePlayerApiV1PlayersUsernameDelete(username)),
    getPlayerMetadataApiV1PlayersUsernameMetadataGet: (username: string) =>
      handleTokenRefresh(() => ApiServices.PlayersService.getPlayerMetadataApiV1PlayersUsernameMetadataGet(username)),
    triggerManualFetchApiV1PlayersUsernameFetchPost: (username: string) =>
      handleTokenRefresh(() => ApiServices.PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username)),
    deactivatePlayerApiV1PlayersUsernameDeactivatePost: (username: string) =>
      handleTokenRefresh(() => ApiServices.PlayersService.deactivatePlayerApiV1PlayersUsernameDeactivatePost(username)),
    reactivatePlayerApiV1PlayersUsernameReactivatePost: (username: string) =>
      handleTokenRefresh(() => ApiServices.PlayersService.reactivatePlayerApiV1PlayersUsernameReactivatePost(username)),
    updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut: (username: string, requestBody: Parameters<typeof ApiServices.PlayersService.updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut>[1]) =>
      handleTokenRefresh(() => ApiServices.PlayersService.updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut(username, requestBody)),
    listPlayerSchedulesApiV1PlayersSchedulesGet: () =>
      handleTokenRefresh(() => ApiServices.PlayersService.listPlayerSchedulesApiV1PlayersSchedulesGet()),
    verifyAllSchedulesApiV1PlayersSchedulesVerifyPost: () =>
      handleTokenRefresh(() => ApiServices.PlayersService.verifyAllSchedulesApiV1PlayersSchedulesVerifyPost()),
  },
  SystemService: {
    ...ApiServices.SystemService,
    getSystemHealthApiV1SystemHealthGet: () =>
      handleTokenRefresh(() => ApiServices.SystemService.getSystemHealthApiV1SystemHealthGet()),
    getDatabaseStatsApiV1SystemStatsGet: () =>
      handleTokenRefresh(() => ApiServices.SystemService.getDatabaseStatsApiV1SystemStatsGet()),
    getPlayerDistributionApiV1SystemDistributionGet: () =>
      handleTokenRefresh(() => ApiServices.SystemService.getPlayerDistributionApiV1SystemDistributionGet()),
    getScheduledTasksApiV1SystemScheduledTasksGet: () =>
      handleTokenRefresh(() => ApiServices.SystemService.getScheduledTasksApiV1SystemScheduledTasksGet()),
    triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost: (taskName: string) =>
      handleTokenRefresh(() => ApiServices.SystemService.triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost(taskName)),
  },
  HistoryService: {
    ...ApiServices.HistoryService,
    getPlayerHistoryApiV1PlayersUsernameHistoryGet: (username: string, startDate?: string | null, endDate?: string | null, days?: number | null) =>
      handleTokenRefresh(() => ApiServices.HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, startDate, endDate, days)),
    getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet: (username: string, skill: string, days?: number) =>
      handleTokenRefresh(() => ApiServices.HistoryService.getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet(username, skill, days)),
    getBossProgressApiV1PlayersUsernameHistoryBossesBossGet: (username: string, boss: string, days?: number) =>
      handleTokenRefresh(() => ApiServices.HistoryService.getBossProgressApiV1PlayersUsernameHistoryBossesBossGet(username, boss, days)),
  },
  StatisticsService: {
    ...ApiServices.StatisticsService,
    getPlayerStatsApiV1PlayersUsernameStatsGet: (username: string) =>
      handleTokenRefresh(() => ApiServices.StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username)),
  },
};

// Export axios instance for custom requests if needed
export { axiosInstance };

// Helper to decode JWT token
export const decodeToken = (token: string) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    return null;
  }
};

