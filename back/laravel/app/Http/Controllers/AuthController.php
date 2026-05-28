<?php

namespace App\Http\Controllers;

use App\Http\Requests\Auth\ChangePasswordRequest;
use App\Http\Requests\Auth\CheckEmailRequest;
use App\Http\Requests\Auth\CheckMobileRequest;
use App\Http\Requests\Auth\FilterUserRequest;
use App\Http\Requests\Auth\ForgetPasswordRequest;
use App\Http\Requests\Auth\LoginByPasswordRequest;
use App\Http\Requests\Auth\LoginByVerificationCodeRequest;
use App\Http\Requests\Auth\ProfileRequest;
use App\Http\Requests\Auth\SetPasswordRequest;
use App\Http\Responses\ApiResponse;
use App\Services\AuthService;

class AuthController extends Controller
{
    protected AuthService $authService;

    public function __construct(AuthService $authService)
    {
        $this->authService = $authService;
    }

    /**
     * @OA\Post(
     *     path="/auth/send/verification",
     *     tags={"Auth"},
     *     summary="ارسال کد تایید",
     *     description="ارسال کد تایید به ایمیل",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"email"},
     *             @OA\Property(property="email", type="string", example="user@example.com")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="کد تایید ارسال شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function sendVerificationCode(CheckEmailRequest $request)
    {
        $data = $this->authService->sendVerificationCode($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Post(
     *     path="/auth/login/verification",
     *     tags={"Auth"},
     *     summary="ورود با کد تایید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"email","verification_code"},
     *             @OA\Property(property="email", type="string", example="user@example.com"),
     *             @OA\Property(property="verification_code", type="string", example="12345")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="ورود موفق",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function loginWithVerificationCode(LoginByVerificationCodeRequest $request)
    {
        $data = $this->authService->loginWithVerificationCode($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Post(
     *     path="/auth/login/password",
     *     tags={"Auth"},
     *     summary="ورود با رمز عبور",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"email","password"},
     *             @OA\Property(property="email", type="string", example="user@example.com"),
     *             @OA\Property(property="password", type="string", example="Password123")
     *         )
     *     ),
     *     @OA\Response(response=200, description="ورود موفق")
     * )
     */
    public function loginWithPassword(LoginByPasswordRequest $request)
    {
        $data = $this->authService->loginWithPassword($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Put(
     *     path="/auth/set/password",
     *     tags={"Auth"},
     *     summary="تنظیم رمز عبور (ثبت‌نام)",
     *     security={{"bearerAuth":{}}},
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"email","password"},
     *             @OA\Property(property="email", type="string", example="user@example.com"),
     *             @OA\Property(property="password", type="string", example="Password123")
     *         )
     *     ),
     *     @OA\Response(response=200, description="رمز ثبت شد")
     * )
     */
    public function setPassword(SetPasswordRequest $request)
    {
        $data = $this->authService->setPassword($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Post(
     *     path="/auth/forget-password",
     *     tags={"Auth"},
     *     summary="فراموشی رمز عبور",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"email","verification_code","password"},
     *             @OA\Property(property="email", type="string", example="user@example.com"),
     *             @OA\Property(property="verification_code", type="string", example="12345"),
     *             @OA\Property(property="password", type="string", example="Password123")
     *         )
     *     ),
     *     @OA\Response(response=200, description="رمز تغییر یافت")
     * )
     */
    public function forgetPassword(ForgetPasswordRequest $request)
    {
        $data = $this->authService->forgetPassword($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Get(
     *     path="/auth/verify/{user_id}",
     *     tags={"Auth"},
     *     summary="تایید کاربر",
     *     security={{"bearerAuth":{}}},
     *     @OA\Parameter(
     *         name="user_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer"),
     *         example=10
     *     ),
     *     @OA\Response(response=200, description="کاربر تایید شد")
     * )
     */
    public function verifyUser($user_id)
    {
        $data = $this->authService->verifyUser($user_id);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Get(
     *     path="/auth/get/me",
     *     tags={"Auth"},
     *     summary="دریافت اطلاعات کاربر",
     *     security={{"bearerAuth":{}}},
     *     @OA\Response(response=200, description="اطلاعات کاربر")
     * )
     */
    public function getMe()
    {
        $data = $this->authService->getMe();
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Post(
     *     path="/auth/change-password",
     *     tags={"Auth"},
     *     summary="تغییر رمز عبور",
     *     security={{"bearerAuth":{}}},
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"current_password","new_password","new_password_confirmation"},
     *             @OA\Property(property="current_password", type="string", example="OldPass123"),
     *             @OA\Property(property="new_password", type="string", example="NewPass123"),
     *             @OA\Property(property="new_password_confirmation", type="string", example="NewPass123")
     *         )
     *     ),
     *     @OA\Response(response=200, description="رمز با موفقیت تغییر یافت")
     * )
     */
    public function changePassword(ChangePasswordRequest $request)
    {
        $data = $this->authService->changePassword($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

    /**
     * @OA\Put(
     *     path="/auth/edit/profile",
     *     tags={"Auth"},
     *     summary="ویرایش پروفایل",
     *     security={{"bearerAuth":{}}},
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="name", type="string", example="علی رضایی"),
     *             @OA\Property(property="birthday", type="string", example="1402/05/19")
     *         )
     *     ),
     *     @OA\Response(response=200, description="پروفایل ویرایش شد")
     * )
     */
    public function editProfile(ProfileRequest $request)
    {
        $data = $this->authService->editProfile($request);
        return ApiResponse::success($data['data'], $data['message']);
    }
    /**
     * @OA\Post(
     *     path="/auth/list-user",
     *     tags={"Auth"},
     *     summary="دریافت لیست کاربران با فیلتر",
     *     security={{"BearerAuth":{}}},
     *
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(
     *                 property="count_item",
     *                 type="integer",
     *                 example=10,
     *                 description="تعداد آیتم‌های مورد نیاز در هر صفحه"
     *             ),
     *             @OA\Property(
     *                 property="is_paginate",
     *                 type="boolean",
     *                 example=true,
     *                 description="فعال بودن یا نبودن صفحه‌بندی"
     *             ),
     *             @OA\Property(
     *                 property="name",
     *                 type="string",
     *                 example="علی رضایی",
     *                 description="فیلتر بر اساس نام کاربر"
     *             ),
     *             @OA\Property(
     *                 property="mobile",
     *                 type="string",
     *                 example="09123456789",
     *                 description="فیلتر بر اساس شماره موبایل"
     *             )
     *         )
     *     ),
     *
     *     @OA\Response(
     *         response=200,
     *         description="لیست کاربران با موفقیت دریافت شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(
     *                 property="data",
     *                 type="object",
     *                 description="لیست کاربران یا دیتای صفحه‌بندی"
     *             )
     *         )
     *     ),
     *
     *     @OA\Response(
     *         response=400,
     *         description="خطا در داده‌های ورودی",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=false),
     *             @OA\Property(property="message", type="string", example="نام باید رشته باشد")
     *         )
     *     )
     * )
     */
    public function listUsers(FilterUserRequest $request){
        $data = $this->authService->listUsers($request);
        return ApiResponse::success($data['data'], $data['message']);
    }

}
