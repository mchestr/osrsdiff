import axios, { AxiosInstance } from 'axios';
import { ApiError } from './core/ApiError';
import { OpenAPI } from './core/OpenAPI';
import { AuthenticationService } from './services/AuthenticationService';
import { HistoryService } from './services/HistoryService';
import { PlayersService } from './services/PlayersService';
import { StatisticsService } from './services/StatisticsService';
import { SystemService } from './services/SystemService';

// Use relative URL when served from same origin, otherwise use env var or localhost
// In development, use empty string to leverage Vite proxy
// In production, use empty string if served from same origin, otherwise use env var
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? '' : '');

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
  AuthenticationService: {
    ...AuthenticationService,
    loginAuthLoginPost: (formData: Parameters<typeof AuthenticationService.loginAuthLoginPost>[0]) =>
      AuthenticationService.loginAuthLoginPost(formData),
    refreshTokenAuthRefreshPost: (requestBody: Parameters<typeof AuthenticationService.refreshTokenAuthRefreshPost>[0]) =>
      AuthenticationService.refreshTokenAuthRefreshPost(requestBody),
    getCurrentUserInfoAuthMeGet: () =>
      handleTokenRefresh(() => AuthenticationService.getCurrentUserInfoAuthMeGet()),
    logoutAuthLogoutPost: () =>
      handleTokenRefresh(() => AuthenticationService.logoutAuthLogoutPost()),
  },
  PlayersService: {
    ...PlayersService,
    addPlayerApiV1PlayersPost: (requestBody: Parameters<typeof PlayersService.addPlayerApiV1PlayersPost>[0]) =>
      handleTokenRefresh(() => PlayersService.addPlayerApiV1PlayersPost(requestBody)),
    listPlayersApiV1PlayersGet: (activeOnly?: boolean) =>
      handleTokenRefresh(() => PlayersService.listPlayersApiV1PlayersGet(activeOnly)),
    removePlayerApiV1PlayersUsernameDelete: (username: string) =>
      handleTokenRefresh(() => PlayersService.removePlayerApiV1PlayersUsernameDelete(username)),
    getPlayerMetadataApiV1PlayersUsernameMetadataGet: (username: string) =>
      handleTokenRefresh(() => PlayersService.getPlayerMetadataApiV1PlayersUsernameMetadataGet(username)),
    getPlayerSummaryApiV1PlayersUsernameSummaryGet: (username: string) =>
      handleTokenRefresh(() => PlayersService.getPlayerSummaryApiV1PlayersUsernameSummaryGet(username)),
    triggerManualFetchApiV1PlayersUsernameFetchPost: (username: string) =>
      handleTokenRefresh(() => PlayersService.triggerManualFetchApiV1PlayersUsernameFetchPost(username)),
    deactivatePlayerApiV1PlayersUsernameDeactivatePost: (username: string) =>
      handleTokenRefresh(() => PlayersService.deactivatePlayerApiV1PlayersUsernameDeactivatePost(username)),
    reactivatePlayerApiV1PlayersUsernameReactivatePost: (username: string) =>
      handleTokenRefresh(() => PlayersService.reactivatePlayerApiV1PlayersUsernameReactivatePost(username)),
    updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut: (username: string, requestBody: Parameters<typeof PlayersService.updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut>[1]) =>
      handleTokenRefresh(() => PlayersService.updatePlayerFetchIntervalApiV1PlayersUsernameFetchIntervalPut(username, requestBody)),
    listPlayerSchedulesApiV1PlayersSchedulesGet: () =>
      handleTokenRefresh(() => PlayersService.listPlayerSchedulesApiV1PlayersSchedulesGet()),
    verifyAllSchedulesApiV1PlayersSchedulesVerifyPost: () =>
      handleTokenRefresh(() => PlayersService.verifyAllSchedulesApiV1PlayersSchedulesVerifyPost()),
  },
    SystemService: {
    ...SystemService,
    getSystemHealthApiV1SystemHealthGet: () =>
      handleTokenRefresh(() => SystemService.getSystemHealthApiV1SystemHealthGet()),
    getDatabaseStatsApiV1SystemStatsGet: () =>
      handleTokenRefresh(() => SystemService.getDatabaseStatsApiV1SystemStatsGet()),
    getPlayerDistributionApiV1SystemDistributionGet: () =>
      handleTokenRefresh(() => SystemService.getPlayerDistributionApiV1SystemDistributionGet()),
    getScheduledTasksApiV1SystemScheduledTasksGet: () =>
      handleTokenRefresh(() => SystemService.getScheduledTasksApiV1SystemScheduledTasksGet()),
    triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost: (taskName: string) =>
      handleTokenRefresh(() => SystemService.triggerScheduledTaskApiV1SystemTriggerTaskTaskNamePost(taskName)),
    getTaskExecutionsApiV1SystemTaskExecutionsGet: (search?: string | null, limit?: number, offset?: number) =>
      handleTokenRefresh(() => SystemService.getTaskExecutionsApiV1SystemTaskExecutionsGet(search, limit, offset)),
  },
  HistoryService: {
    ...HistoryService,
    getPlayerHistoryApiV1PlayersUsernameHistoryGet: (username: string, startDate?: string | null, endDate?: string | null, days?: number | null) =>
      handleTokenRefresh(() => HistoryService.getPlayerHistoryApiV1PlayersUsernameHistoryGet(username, startDate, endDate, days)),
    getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet: (username: string, skill: string, days?: number) =>
      handleTokenRefresh(() => HistoryService.getSkillProgressApiV1PlayersUsernameHistorySkillsSkillGet(username, skill, days)),
    getBossProgressApiV1PlayersUsernameHistoryBossesBossGet: (username: string, boss: string, days?: number) =>
      handleTokenRefresh(() => HistoryService.getBossProgressApiV1PlayersUsernameHistoryBossesBossGet(username, boss, days)),
  },
  StatisticsService: {
    ...StatisticsService,
    getPlayerStatsApiV1PlayersUsernameStatsGet: (username: string) =>
      handleTokenRefresh(() => StatisticsService.getPlayerStatsApiV1PlayersUsernameStatsGet(username)),
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

