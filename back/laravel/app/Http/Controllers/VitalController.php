<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Http\Responses\ApiResponse;
use MongoDB\Client as MongoClient;
use PhpMqtt\Client\MqttClient;
use PhpMqtt\Client\ConnectionSettings;

class VitalController extends Controller
{
    private $db;

    public function __construct()
    {
        $mongoUri = env('MONGO_URI', 'mongodb://127.0.0.1:27017');
        $client = new MongoClient($mongoUri);
        $this->db = $client->echo_pipeline;
    }

    /**
     * منشی session اندازه‌گیری رو شروع می‌کنه
     * POST /api/vitals/start
     */
    public function startSession(Request $request)
    {
        $patientId = $request->input('patient_id');
        $deviceId  = $request->input('device_id', 'ESP32_001');

        if (!$patientId) {
            return ApiResponse::error('patient_id الزامی است', 422);
        }

        // session قبلی رو ببند
        $this->db->vital_sessions->updateMany(
            ['device_id' => $deviceId, 'status' => 'active'],
            ['$set' => ['status' => 'stopped', 'stopped_at' => new \MongoDB\BSON\UTCDateTime()]]
        );

        // session جدید بساز
        $startedAt = new \MongoDB\BSON\UTCDateTime();
        $this->db->vital_sessions->insertOne([
            'patient_id' => (int)$patientId,
            'device_id'  => $deviceId,
            'status'     => 'active',
            'started_by' => auth()->id(),
            'created_at' => $startedAt,
        ]);

        // دستور start رو از طریق MQTT به ESP32 ارسال کن
        $this->publishCommand($deviceId, [
            'action'     => 'start',
            'patient_id' => (int)$patientId,
        ]);

        return ApiResponse::success([
            'device_id'  => $deviceId,
            'patient_id' => $patientId,
            // زمان سرور بر حسب میلی‌ثانیه — فرانت با ?since= همین را می‌فرستد
            // تا فقط خوانده‌های همین session برگردند (نه داده‌های قدیمی)
            'started_at' => (string)$startedAt,
        ], 'اندازه‌گیری شروع شد');
    }

    /**
     * توقف اندازه‌گیری
     * POST /api/vitals/stop
     */
    public function stopSession(Request $request)
    {
        $deviceId = $request->input('device_id', 'ESP32_001');

        $this->db->vital_sessions->updateMany(
            ['device_id' => $deviceId, 'status' => 'active'],
            ['$set' => ['status' => 'stopped', 'stopped_at' => new \MongoDB\BSON\UTCDateTime()]]
        );

        $this->publishCommand($deviceId, ['action' => 'stop']);

        return ApiResponse::success(null, 'اندازه‌گیری متوقف شد');
    }

    /**
     * خوانده‌های زنده برای بیمار (فرانت هر ۲ ثانیه poll می‌کنه، هم‌زمان با بازه انتشار ESP32)
     * GET /api/vitals/live/{patient_id}?since=<epoch_ms>
     *
     * since: زمان شروع session (میلی‌ثانیه) — فقط خوانده‌های همین session برمی‌گردند
     *        تا نمودار با داده‌های session های قبلی قاطی نشود
     */
    public function getLive(Request $request, $patientId)
    {
        $filter = ['patient_id' => (int)$patientId];

        $since = $request->query('since');
        if ($since && ctype_digit((string)$since)) {
            $filter['recorded_at'] = ['$gte' => new \MongoDB\BSON\UTCDateTime((int)$since)];
        }

        $readings = $this->db->vital_readings->find(
            $filter,
            [
                'sort'  => ['_id' => -1],
                'limit' => 200,
            ]
        )->toArray();

        $data = array_map(fn($r) => [
            'heart_rate' => $r->heart_rate ?? null,
            'valid_hr'   => $r->valid_hr ?? false,
            'recorded_at'=> isset($r->recorded_at) ? (string)$r->recorded_at : null,
        ], $readings);

        // ترتیب صعودی برای نمودار
        $data = array_reverse($data);

        return ApiResponse::success($data);
    }

    /**
     * ذخیره میانگین در patient_profiles
     * PATCH /api/vitals/save/{patient_id}
     */
    public function saveToProfile(Request $request, $patientId)
    {
        // میانگین آخرین ۳۰ reading معتبر رو حساب کن
        $readings = $this->db->vital_readings->find(
            ['patient_id' => (int)$patientId, 'valid_hr' => true],
            ['sort' => ['_id' => -1], 'limit' => 30]
        )->toArray();

        if (empty($readings)) {
            return ApiResponse::error('داده‌ای برای ذخیره وجود ندارد', 422);
        }

        $avgHr = (int)round(array_sum(array_map(fn($r) => $r->heart_rate ?? 0, $readings)) / count($readings));

        $update = [
            'thalach'              => $avgHr,
            'last_vital_reading_at'=> new \MongoDB\BSON\UTCDateTime(),
            'updated_at'           => new \MongoDB\BSON\UTCDateTime(),
        ];

        $existing = $this->db->patient_profiles->findOne(['user_id' => (int)$patientId]);

        if ($existing) {
            $this->db->patient_profiles->updateOne(
                ['user_id' => (int)$patientId],
                ['$set' => $update]
            );
        } else {
            $update['user_id']    = (int)$patientId;
            $update['created_at'] = new \MongoDB\BSON\UTCDateTime();
            $this->db->patient_profiles->insertOne($update);
        }

        return ApiResponse::success(['avg_hr' => $avgHr], 'در پروفایل بیمار ذخیره شد');
    }

    /**
     * ارسال command به ESP32 از طریق MQTT
     */
    private function publishCommand(string $deviceId, array $payload): void
    {
        $host  = env('MQTT_HOST', '127.0.0.1');
        $port  = (int)env('MQTT_PORT', 1883);
        $topic = "devices/{$deviceId}/cmd";

        try {
            $mqtt = new MqttClient($host, $port, 'laravel-publisher-' . uniqid());
            $settings = (new ConnectionSettings())->setConnectTimeout(3);
            $mqtt->connect($settings);
            $mqtt->publish($topic, json_encode($payload), 0);
            $mqtt->disconnect();
        } catch (\Exception $e) {
            \Log::warning("MQTT publish failed: " . $e->getMessage());
        }
    }
}
