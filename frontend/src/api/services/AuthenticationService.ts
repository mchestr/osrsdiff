/* generated using openapi-typescript-codegen -- do no edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { Body_login_auth_login_post } from '../models/Body_login_auth_login_post';
import type { TokenRefreshRequest } from '../models/TokenRefreshRequest';
import type { TokenRefreshResponse } from '../models/TokenRefreshResponse';
import type { TokenResponse } from '../models/TokenResponse';
import type { UserResponse } from '../models/UserResponse';

import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class AuthenticationService {

    /**
     * Login
     * Login endpoint to generate JWT tokens.
     *
     * Compatible with OAuth2 password flow for OpenAPI docs integration.
     * @param formData
     * @returns TokenResponse Successful Response
     * @throws ApiError
     */
    public static loginAuthLoginPost(
        formData: Body_login_auth_login_post,
    ): CancelablePromise<TokenResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/login',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Refresh Token
     * Refresh access token using refresh token.
     * @param requestBody
     * @returns TokenRefreshResponse Successful Response
     * @throws ApiError
     */
    public static refreshTokenAuthRefreshPost(
        requestBody: TokenRefreshRequest,
    ): CancelablePromise<TokenRefreshResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/refresh',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    /**
     * Get Current User Info
     * Get current authenticated user information.
     *
     * This endpoint demonstrates how to use the authentication dependency.
     * @returns UserResponse Successful Response
     * @throws ApiError
     */
    public static getCurrentUserInfoAuthMeGet(): CancelablePromise<UserResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/auth/me',
        });
    }

    /**
     * Logout
     * Logout endpoint that blacklists the current access token.
     * @returns string Successful Response
     * @throws ApiError
     */
    public static logoutAuthLogoutPost(): CancelablePromise<Record<string, string>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/auth/logout',
        });
    }

}
