<?php

namespace App\Models;

use App\Enums\UserType;
use App\Exceptions\ErrorException;
use App\Http\Requests\Auth\CheckMobileAndUsernameRequest;
use App\Http\Requests\Auth\ConfirmCodeRequest;
use App\Http\Requests\Auth\RegisterUserRequest;
use App\Http\Requests\Setting\SettingKeyRequest;
use App\Http\Requests\Setting\SettingUpdateRequest;
use App\Http\Requests\User\ProfileRequest;
use App\Models\Setting;
use App\Models\User;
use Auth;
use Carbon\Carbon;
use Illuminate\Database\Eloquent\Collection;
use Illuminate\Support\Facades\Hash;
use Ramsey\Uuid\Uuid;
use Illuminate\Support\Str;
class SettingService
{


    public function __construct()
    {

    }


    public function getSetting()
    {
        $data=Setting::all();
        return [
            "data"=>$data,
            "message"=>""
        ];
    }
    public function getSettingWithKey(SettingKeyRequest $request)
    {
        $data=Setting::where(['key'=>$request->key])->first();
        return [
            "data"=>$data,
            "message"=>""
        ];
    }

    public function updateSetting(SettingUpdateRequest $request)
    {
        Setting::set($request->key, $request->value);
        return [
            "data"=>null,
            "message"=>"عملیات ثبت موفقیت امیز بود"
        ];
    }






}
