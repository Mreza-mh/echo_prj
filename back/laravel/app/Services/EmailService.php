<?php

namespace App\Services;

use App\Mail\EmailVerificationCode;
use Illuminate\Support\Facades\Mail;

class EmailService
{
    public function sendVerificationCodeEmail(string $email, string $code)
    {
         Mail::to($email)->send(new EmailVerificationCode($code));
    }
}
