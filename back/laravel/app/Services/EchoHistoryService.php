<?php

namespace App\Services;

use App\Exceptions\ErrorException;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

class EchoHistoryService
{
    private function connectMongoDB(){
        $data = DB::connection('mongodb')->table('acaree')->get();
        return $data;
    }

    public function getInfo($patient_id = null){
        $data = $this->connectMongoDB();
        if($patient_id == null){
            $patient_id = Auth::id();
        }
        $data = $data->where('patient_id', $patient_id)->first();
        if(!$data){
            throw new ErrorException('اکوی بیمار وجود ندارد');
        }
        return [
            "message" => "اطلاعات اکو بیمار با موفقیت ارسال شد",
            "data" => $data
        ];
    }

    public function getFile($address)
    {
        $basePath = public_path('echos');
        $path = realpath($basePath . '/' . $address);

        if (!$path || !str_starts_with($path, $basePath)) {
            throw new ErrorException('Invalid file path');
        }

        if (!file_exists($path)) {
            throw new ErrorException('File not found');
        }

        return $path;
    }


}
