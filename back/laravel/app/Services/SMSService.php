<?php

namespace App\Services;
use App\Exceptions\ErrorException;
use Ipe\Sdk\Facades\SmsIr;
use Illuminate\Support\Facades\Log;

class SMSService
{
    public function sendSMSConfirmCode(string $mobile, string $code)
    {
        Log::info("کد تایید برای شماره $mobile ارسال شد: $code");

//        try {
//
//            $templateId = 377889; // شناسه الگو
//            $parameters = [
//                    [
//                        "name" => "code",
//                        "value" => $code
//                    ],
//
//            ];
//
//            $response = SmsIr::verifySend($mobile, $templateId, $parameters);
//
//        } catch (\Exception $e) {
//
//
//                throw new ErrorException($e);
//
//        }
    }
}
