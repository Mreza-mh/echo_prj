<?php

namespace App\Http\Controllers;

use Illuminate\Support\Facades\Auth;
use Illuminate\Http\Request;
use App\Http\Responses\ApiResponse;
use Illuminate\Support\Facades\Validator;
use MongoDB\Client as MongoClient;

class PatientDataController extends Controller  #ذخیره و بازیابی اطلاعات پزشکی بیماران از مونگو
{
    private $collection;

    public function __construct()
    {
        $mongoUri = env('MONGO_URI', 'mongodb://127.0.0.1:27017');
        $client = new MongoClient($mongoUri);
        $this->collection = $client->echo_pipeline->patient_profiles;  #اتصال به کالکشن
    }

    public function store(Request $request)
    {
        $validator = Validator::make($request->all(), [  #اعتبارسنجی
            'age' => 'nullable|integer|min:18|max:120',
            'gender' => 'nullable|integer|in:1,2',
            'sex' => 'nullable|integer|in:0,1',
            'height' => 'nullable|numeric|min:100|max:230',
            'weight' => 'nullable|numeric|min:30|max:250',
            'ap_hi' => 'nullable|integer|min:60|max:300',
            'ap_lo' => 'nullable|integer|min:40|max:200',
            'cholesterol' => 'nullable|integer|in:1,2,3',
            'gluc' => 'nullable|integer|in:1,2,3',
            'smoke' => 'nullable|integer|in:0,1',
            'alco' => 'nullable|integer|in:0,1',
            'active' => 'nullable|integer|in:0,1',
            'cp' => 'nullable|integer|in:0,1,2,3',
            'trestbps' => 'nullable|integer|min:60|max:250',
            'chol' => 'nullable|integer|min:100|max:600',
            'fbs' => 'nullable|integer|in:0,1',
            'restecg' => 'nullable|integer|in:0,1,2',
            'thalach' => 'nullable|integer|min:40|max:220',
            'exang' => 'nullable|integer|in:0,1',
            'oldpeak' => 'nullable|numeric|min:0|max:6.2',
            'slope' => 'nullable|integer|in:0,1,2',
            'ca' => 'nullable|integer|in:0,1,2,3,4',
            'thal' => 'nullable|integer|in:0,1,2,3',
        ]);

        if ($validator->fails()) {
            return ApiResponse::error($validator->errors()->first(), 422);
        }

        $data = $request->only([
            'age', 'gender', 'sex', 'height', 'weight', 'ap_hi', 'ap_lo',
            'cholesterol', 'gluc', 'smoke', 'alco', 'active', 'cp', 'trestbps',
            'chol', 'fbs', 'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'
        ]);

        $userId = $request->input('user_id') ?? Auth::id();

        if (!$userId) {
            return ApiResponse::error('شناسه کاربر یافت نشد', 401);
        }

        if (isset($data['ap_hi']) && isset($data['ap_lo']) && $data['ap_hi'] <= $data['ap_lo']) {
            return ApiResponse::error('فشار خون سیستولیک باید بزرگتر از دیاستولیک باشد', 422);
        }

        // حذف فیلدهای null
        $data = array_filter($data, fn($v) => $v !== null);
        $data['user_id'] = (int)$userId;
        $data['updated_at'] = new \MongoDB\BSON\UTCDateTime();

        $existing = $this->collection->findOne(['user_id' => (int)$userId]);

        if ($existing) {  #اگه کاربر قبلا وجود داشته باشه اپدیت میکنه درغیراینصورت یه کاربر جدید میسازه
            $this->collection->updateOne(
                ['user_id' => (int)$userId],
                ['$set' => $data]
            );
            $message = 'اطلاعات با موفقیت به‌روزرسانی شد';
        } else {
            $data['created_at'] = new \MongoDB\BSON\UTCDateTime();
            $this->collection->insertOne($data);
            $message = 'اطلاعات با موفقیت ذخیره شد';
        }

        return ApiResponse::success($data, $message);
    }

    public function show($userId)
    {
        $patient = $this->collection->findOne(['user_id' => (int)$userId]);

        if (!$patient) {
            return ApiResponse::error('اطلاعات بیمار یافت نشد', 404);
        }

        $data = json_decode(json_encode($patient), true);  #_id رو که ایدی خود مونگوعه حذف میکنه
        unset($data['_id']);

        return ApiResponse::success($data);
    }
}
