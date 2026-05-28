<?php

namespace App\Services;

use App\Enums\LoginMethod;
use App\Enums\SettingKey;
use App\Exceptions\ErrorException;
use App\Http\Requests\Auth\CheckEmailRequest;
use App\Http\Requests\Auth\FilterUserRequest;
use App\Http\Requests\Auth\ForgetPasswordRequest;
use App\Http\Requests\Auth\LoginByPasswordRequest;
use App\Http\Requests\Auth\LoginByVerificationCodeRequest;
use App\Http\Requests\Auth\ProfileRequest;
use App\Http\Requests\Auth\SetPasswordRequest;
use App\Http\Requests\Auth\CheckMobileRequest;
use App\Http\Requests\Auth\ChangePasswordRequest;
use App\Models\Setting;
use App\Models\User;
use Hekmatinasser\Verta\Verta;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Carbon\Carbon;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log;

class AuthService
{
    protected EmailService $emailService;

    public function __construct(EmailService $emailService)
    {
        $this->emailService = $emailService;
    }

    public function sendVerificationCode(CheckEmailRequest $request)
    {
        $email = strtolower($request->email);

        // بررسی کاربر موجود یا ایجاد جدید
        $user = User::where('email', $email)->first();
        if (!$user) {
            $user = User::create(['email' => $email]);
        }

        $has_password = $user->password != null ? true : false;

        $message = 'با گذرواژه خود وارد شوید';
        if (!$has_password || $request->force_by_sms || $request->forget_password) {
            if ($user->email_verification_expires_at && $user->email_verification_expires_at > now()) {
                $remainingTime = now()->diffInSeconds(Carbon::parse($user->email_verification_expires_at));
                throw new ErrorException('کد تأیید قبلی هنوز معتبر است. لطفاً ' . round($remainingTime) . ' ثانیه دیگر تلاش کنید.');
            }

            $code = rand(10000, 99999);
            $user->email_verification_code = $code;
            $user->email_verification_expires_at = now()->addMinutes(2);
            $user->save();

            // ارسال ایمیل
            $this->emailService->sendVerificationCodeEmail($email, $code);

            $message = 'کد تایید ارسال شد';
        }

        return [
            'message' => $message,
            'data' => [
                'has_password' => $has_password,
                'forget_password' => $request->filled('forget_password') && $request->forget_password ? $request->forget_password : false,
                'force_by_sms' => $request->filled('force_by_sms') ? $request->force_by_sms : false,
            ]
        ];
    }

    public function loginWithVerificationCode(LoginByVerificationCodeRequest $request)
    {
        $email = strtolower($request->email);
        $user = User::where('email', $email)
            ->where('email_verification_code', $request->verification_code)
            ->where('email_verification_expires_at', '>', now())
            ->first();
        if (!$user) {
            throw new ErrorException('اطلاعات ورودی صحیح نیست');
        }
        $user->email_verified_at = now();
        $user->save();

        $token = $user->createToken('token',$user->getScope())->accessToken;

        return [
            'message' => '',
            'data' => [
                'token' => $token,
                'user' => $user,
                'has_password' => $user->password != null ? true : false,
                'force_by_sms' => $request->filled('force_by_sms') ? $request->force_by_sms : false,
            ]
        ];
    }

    public function loginWithPassword(LoginByPasswordRequest $request)
    {
        $email = strtolower($request->email);
        $user = User::where('email', $email)->first();
        if (!$user) {
            throw new ErrorException('اطلاعات ورودی صحیح نیست');
        }

        if ($user && Auth::attempt(['email' => $email, 'password' => $request->password])) {
            $token = $user->createToken('token', $user->getScope())->accessToken;
            return [
                'message' => '',
                'data' => [
                    'token' => $token,
                    'user' => $user,
                    'has_password' => $user->password != null ? true : false
                ]
            ];
        }
        throw new ErrorException('اطلاعات ورودی صحیح نیست');
    }

    public function setPassword(SetPasswordRequest $request)
    {
        $user = User::where(['id' => Auth::id()])->first();
        if (!$user) {
            throw new ErrorException('کاربری یافت نشد');
        }
        $user->password = bcrypt($request->password);
        $user->email = strtolower($request->email);
        $user->save();
        return [
            'message' => 'گذرواژه تنظیم شد',
            'data' => $user
        ];
    }

    public function forgetPassword(ForgetPasswordRequest $request)
    {
        $email = strtolower($request->email);
        $code = rand(10000, 99999);
        $this->emailService->sendVerificationCodeEmail($email, $code);


        $user = User::where('email', $email)
            ->where('email_verification_code', $request->verification_code)
            ->where('email_verification_expires_at', '>', now())
            ->first();
        if (!$user) {
            throw new ErrorException('اطلاعات ورودی صحیح نیست');
        }

        $user->password = bcrypt($request->password);
        $user->email_verification_code = null;
        $user->email_verification_expires_at = null;
        $user->tokens()->delete();
        $user->save();

        Log::info('Password reset completed', [
            'user_id' => $user->id,
            'email' => $user->email,
            'ip' => request()->ip(),
            'user_agent' => request()->userAgent()
        ]);

        return [
            'message' => 'گذرواژه جدید ثبت شد',
            'data' => [
                'user' => $user,
                'has_password' => $user->password != null ? true : false
            ]
        ];
    }

    public function verifyUser($user_id)
    {
        $user = User::where(['id' => $user_id])->first();
        if (!$user) {
            throw new ErrorException('کاربری یافت نشد');
        }
        $user->is_verify = !$user->is_verify;
        $user->save();

        return [
            'message' => 'تغییر احراز هویت انجام شد',
            'data' => $user
        ];
    }

    public function changePassword(ChangePasswordRequest $request)
    {
        $user = Auth::user();
        if (!Hash::check($request->current_password, $user->password)) {
            throw new ErrorException('رمز عبور فعلی اشتباه است');
        }

        $user->password = bcrypt($request->new_password);
        $currentToken = $user->currentAccessToken();
        $user->tokens()->where('id', '!=', $currentToken->id)->delete();
        $user->save();

        Log::info('Password changed by user', [
            'user_id' => $user->id,
            'mobile' => $user->mobile,
            'email' => $user->email,
            'ip' => request()->ip(),
            'user_agent' => request()->userAgent()
        ]);

        return [
            'message' => 'رمز عبور با موفقیت تغییر کرد',
            'data' => null
        ];
    }

    public function getMe()
    {
        $user = User::find(Auth::user()->id);
        if (is_null($user)) {
            throw new \ErrorException('کاربری یافت نشد');
        }
        if ($user->birthday) {
            $user->birthday = Verta::instance($user->birthday)->format('Y/m/d');
        }
        return [
            'message' => 'عملیات موفق',
            'data' => $user
        ];
    }

    public function editProfile(ProfileRequest $request)
    {
        $user =User::where(['id' => Auth::id()])->first();
        if (!$user) {
            throw new ErrorException('کاربری یافت نشد');
        }
        if($request->filled('name')){
            $user->name = $request->name;
        }
        if($request->filled('profile_image_id')){
            $user->profile_image_id = $request->profile_image_id;
        }
        if ($request->filled('birthday')) {
            // تبدیل به تاریخ میلادی با استفاده از Verta
            $verta = Verta::parseFormat('Y/m/d', $request->birthday);
            $date = Verta::jalaliToGregorian($verta->year, $verta->month, $verta->day);
            $date = $date[0] . '-' . $date[1] . '-' . $date[2];
            $expireDate = Carbon::parse($date)->format('Y-m-d');

            // تبدیل به Carbon تا بشه ذخیره کرد
            $user->birthday = $date;
        }
        $user->save();
        return [
            'message' => 'پروفایل ثبت شد',
            'data' => $user
        ];
    }


    public function listUsers(FilterUserRequest $request){
        $is_paginate = $request->filled('is_paginate') ? filter_var($request->is_paginate, FILTER_VALIDATE_BOOLEAN) : false;
        $count_item = $request->filled('count_item') ? filter_var($request->count_item, FILTER_VALIDATE_INT) : 10;

        $query = User::query();

        if($request->filled('name')){
            $query->where('name', 'like', '%' . $request->name . '%');
        }

        if($request->filled('mobile')){
            $query->where('mobile', 'like', '%' . $request->mobile . '%');
        }

        $data = $is_paginate ? $query->paginate($count_item) : $query->get();

        return [
            'message' => 'عملیات موفق',
            'data' => $data
        ];
    }



}

