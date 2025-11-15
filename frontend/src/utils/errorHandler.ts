import { ApiError } from '../api/core/ApiError';

/**
 * Extracts error message from various error types consistently
 */
export const extractErrorMessage = (error: unknown, fallback = 'An unexpected error occurred'): string => {
  if (error instanceof ApiError) {
    return error.body?.detail || error.message || fallback;
  }

  if (error instanceof Error) {
    return error.message || fallback;
  }

  // Handle axios-style errors
  const axiosError = error as { response?: { data?: { detail?: string } }; body?: { detail?: string } };
  if (axiosError?.response?.data?.detail) {
    return axiosError.response.data.detail;
  }
  if (axiosError?.body?.detail) {
    return axiosError.body.detail;
  }

  return fallback;
};

/**
 * Type guard to check if error has a detail property
 */
export const hasErrorDetail = (error: unknown): error is { body?: { detail?: string } } => {
  return (
    typeof error === 'object' &&
    error !== null &&
    ('body' in error || 'response' in error)
  );
};

