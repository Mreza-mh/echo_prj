<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use MongoDB\Client as MongoClient;
use PhpMqtt\Client\MqttClient;
use PhpMqtt\Client\ConnectionSettings;

class MqttListenCommand extends Command
{
    protected $signature   = 'mqtt:listen';
    protected $description = 'Subscribe to MQTT broker and save vital readings to MongoDB';

    public function handle(): void
    {
        $host = env('MQTT_HOST', '127.0.0.1');
        $port = (int)env('MQTT_PORT', 1883);

        $mongoUri   = env('MONGO_URI', 'mongodb://127.0.0.1:27017');
        $mongoClient = new MongoClient($mongoUri);
        $collection  = $mongoClient->echo_pipeline->vital_readings;

        $this->info("Connecting to MQTT broker at {$host}:{$port}...");

        // اتصال ممکن است به دلایل شبکه‌ای (ری‌استارت بروکر، قطعی موقت WiFi و ...)
        // با EOF قطع شود. به‌جای کرش کل دستور، دوباره وصل می‌شویم تا listener
        // همیشه فعال بماند (Ctrl+C برای توقف کامل).
        while (true) {
            try {
                // clientId یکتا در هر تلاش تا بروکر کانکشن قبلی معلق را با «duplicate client id» قطع نکند
                $mqtt = new MqttClient($host, $port, 'laravel-listener-' . uniqid());
                $settings = (new ConnectionSettings())
                    ->setKeepAliveInterval(30)
                    ->setConnectTimeout(10)
                    ->setSocketTimeout(5);
                $mqtt->connect($settings, true);

                $this->info('Subscribed to devices/+/data');

                // دریافت هر reading از ESP32 و ذخیره در MongoDB
                $mqtt->subscribe('devices/+/data', function (string $topic, string $message) use ($collection) {
                    $payload = json_decode($message, true);

                    if (!$payload || !isset($payload['patient_id'])) {
                        return;
                    }

                    $collection->insertOne([
                        'patient_id' => (int)$payload['patient_id'],
                        'device_id'  => $payload['device_id'] ?? 'unknown',
                        'heart_rate' => (int)($payload['hr'] ?? 0),
                        'valid_hr'   => (bool)($payload['valid_hr'] ?? false),
                        'recorded_at'=> new \MongoDB\BSON\UTCDateTime(),
                    ]);

                    $this->line("[{$topic}] HR={$payload['hr']} patient={$payload['patient_id']}");
                }, 0);

                $mqtt->loop(true);
            } catch (\Throwable $e) {
                $this->warn('MQTT connection lost: ' . $e->getMessage() . ' — reconnecting in 3s...');
                \Log::warning('mqtt:listen reconnecting after error: ' . $e->getMessage());
                sleep(3);
            }
        }
    }
}
