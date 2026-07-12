<?php

namespace App\Services;

use App\Exceptions\ErrorException;
use Illuminate\Support\Facades\Auth;

class EchoHistoryService
{
    private ?\MongoDB\Driver\Manager $mongoManager = null;

    private function mongoUri(): string
    {
        $dsn = env('MONGO_DB_DSN', env('ECHO_MONGO_URI'));
        if ($dsn) {
            return $dsn;
        }

        $host = env('MONGO_DB_HOST', '127.0.0.1');
        $port = env('MONGO_DB_PORT', 27017);
        $username = env('MONGO_DB_USERNAME');
        $password = env('MONGO_DB_PASSWORD');
        $credentials = '';

        if ($username !== null && $username !== '') {
            $credentials = rawurlencode($username) . ':' . rawurlencode((string) $password) . '@';
        }

        return "mongodb://{$credentials}{$host}:{$port}/";
    }

    private function databaseName(): string
    {
        return env('MONGO_DB_DATABASE', env('ECHO_MONGO_DB', 'echo_pipeline'));
    }

    private function collectionName(): string
    {
        return env('MONGO_DB_COLLECTION', env('ECHO_MONGO_COLLECTION', 'patients'));
    }

    private function collectionNamespace(): string
    {
        return $this->databaseName() . '.' . $this->collectionName();
    }

    private function manager(): \MongoDB\Driver\Manager
    {
        if (!$this->mongoManager) {
            $this->mongoManager = new \MongoDB\Driver\Manager($this->mongoUri());
        }

        return $this->mongoManager;
    }

    public function getInfo($patient_id = null): array
    {
        $patientId = $this->resolvePatientId($patient_id);  # یا ایدی که بعنوان پارامتر اومده میاد یا ایدی کاربر لاگین شده(خود بیمار)
        $document = $this->findPatientDocument($patientId); #داکیومنت بیمار رو میره از مونگو میکشه بیرون

        if (!$document) {
            throw new ErrorException('Echo history not found');
        }

        $data = $this->normalizeMongoValue($document);   #تبدیل خروجی مونگو به فرمت ph
        $data['patient_id'] = (string) ($data['_id'] ?? $patientId);
        $data = $this->appendFileLinks($data);  #دیتای خام رو به دیتای قابل استفاده برای فرانت‌اند تبدیل می‌کنه، بدون اینکه لازم باشه برنامه‌نویس فرانت‌اند دستی مسیرها رو پردازش کنه.

        return [
            'message' => 'Echo history loaded successfully',
            'data' => $data,
        ];
    }

    public function getFile($address): string   #مسیرو فایلو میگیره ، ادرسش رو سرور روو برمیگردونه : برای دانلود
    {
        $basePath = realpath(public_path('echos'));  # مسیرش از public رو میگیره
        if (!$basePath) {
            throw new ErrorException('Echo public directory not found');
        }

        $normalizedAddress = $this->normalizeFileAddress($address); #ادرس نسبی شو میسازه
        if (!$normalizedAddress) {
            throw new ErrorException('Invalid file path');
        }

        #مسیر رو از بابت ایمنی چک میکنه
        $candidate = realpath($basePath . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $normalizedAddress));
        if (!$candidate || !$this->isPathInside($candidate, $basePath)) {
            throw new ErrorException('Invalid file path');
        }

        if (!file_exists($candidate)) {
            throw new ErrorException('File not found');
        }

        return $candidate;
    }

    private function resolvePatientId($patientId): string
    {
        if ($patientId !== null && $patientId !== '') {
            return (string) $patientId;
        }

        $user = Auth::user();
        return (string) ($user->patient_id ?? $user->id ?? Auth::id());
    }

    private function findPatientDocument(string $patientId)
    {
        // مقادیر Mongo ممکن است رشته‌ای یا عددی ذخیره شده باشند؛ هر دو نوع را امتحان می‌کنیم
        #پس یه ارایه میسازیم که هم مقدار رشته ای رو بگیره هم مقدار عددی رو
        $candidates = [$patientId];
        if (ctype_digit($patientId)) {
            $candidates[] = (int) $patientId;
        }

        #ایدی بیمار ممکنه تو یکی از این سه جا ذخیره شده باشه پس سهتاشو بررسی میکنیم
        foreach (['_id', 'patient_info.id', 'patient_id'] as $field) {
            foreach ($candidates as $candidate) {
                $document = $this->findOne([$field => $candidate]);
                if ($document) {
                    return $document;
                }
            }
        }

        return null;
    }

    private function findOne(array $filter)
    {
        try {
            $query = new \MongoDB\Driver\Query($filter, ['limit' => 1]);
            $cursor = $this->manager()->executeQuery($this->collectionNamespace(), $query); #یه کوئری مزنه رو کالکشن و اولین سندی که برای اون ایدی بیماره برمیگردونه

            foreach ($cursor as $document) {
                return $document;
            }
        } catch (\Throwable $exception) {
            throw new ErrorException('MongoDB connection failed: ' . $exception->getMessage());
        }

        return null;
    }

    private function normalizeMongoValue($value)  #تبدیل خروجی های مونگو به ساختاارهای مناسب تو php,api response
    {
        if ($value instanceof \Illuminate\Support\Collection) {  # اگه از نوع کالکشن لاراول بود به ارایه ساده تبدیل کن
            $value = $value->all();
        }

        if ($value instanceof \MongoDB\Model\BSONDocument || $value instanceof \MongoDB\Model\BSONArray) { #اگه از نوع ابجکت های مدرن تو مونگو بود به ارایه تبدیل کن
            $value = $value->getArrayCopy();
        }

        if ($value instanceof \MongoDB\BSON\ObjectId) { # ObjectId("507f1f77bcf86cd799439011") => "507f1f77bcf86cd799439011"
            return (string) $value;
        }

        if ($value instanceof \MongoDB\BSON\UTCDateTime) {  #تاریخ هایی که تو فرمت مونگو هست رو به فرمت استاندارد خودمون تبدیل میکنه
            return $value->toDateTime()->format(DATE_ATOM);
        }

        if (is_object($value)) {  # اگه هیچ کدوم از بالاییا نبود ولی از نوع ابجکت بود ارایه کن
            $value = get_object_vars($value);
        }

        if (is_array($value)) {  #پردازش بازگشتی برای مقادیر تو در تو
            foreach ($value as $key => $item) {
                $value[$key] = $this->normalizeMongoValue($item);
            }
        }

        return $value;
    }

    private function appendFileLinks($value, ?string $parentKey = null)
    {
        if (!is_array($value)) { #اگه ورودی ارایه نبود که برگردونش
            return $value;
        }

        foreach ($value as $key => $item) {
            if (is_array($item)) {  #اگه ارایه تو در تو بود بازگشتی بزن
                $value[$key] = $this->appendFileLinks($item, is_string($key) ? $key : $parentKey);
                continue;
            }

            if (!is_string($item) || !$this->looksLikePublicFilePath($item)) { #اگه شبیه فایلای عمومی و معتبر نبود ردش کن
                continue;
            }

            $address = $this->normalizeFileAddress($item); #مسیر نسبی استانداردشو بساز
            if (!$address) { #اگهمیر نامعتبر شد ردش کن
                continue;
            }

            if (is_string($key)) { #تکمیل اطلاعات
                $value[$key . '_address'] = $address;  #اضافه کردن ادرس نسبی
                $value[$key . '_url'] = $this->fileUrl($address);  #لینک دانلود
                $value[$key . '_exists'] = $this->publicFileExists($address);  #ایا فایل رو سروره؟
            }
        }

        if ($this->isStringList($value) && $this->looksLikeFileList($parentKey, $value)) { # اگه کل فایل یه لیست از ادرسها یا رشته های سادس
            return [ #فرمت خروجی متفاوت میشه
                'items' => array_values($value),
                'links' => array_values(array_filter(array_map(function ($path) {
                    $address = $this->normalizeFileAddress($path);

                    if (!$address) {
                        return null;
                    }

                    return [
                        'path' => $path,
                        'address' => $address,
                        'url' => $this->fileUrl($address),
                        'exists' => $this->publicFileExists($address),
                    ];
                }, $value))),
            ];
        }

        return $value;
    }

    private function normalizeFileAddress(?string $path): ?string  #پاکسازی مسیر فایلا برای اینکه یه مسیر نسبی استاندارد برای فایلا بسازه
    {
        if (!$path) {
            return null;
        }

        $path = rawurldecode($path);
        $path = str_replace('\\', '/', trim($path));
        $path = preg_replace('#/+#', '/', $path);
        $path = ltrim($path, '/');

        $markers = [
            'back/laravel/public/echos/',
            'laravel/public/echos/',
            'public/echos/',
            'echos/',
        ];

        foreach ($markers as $marker) {
            $position = stripos($path, $marker);
            if ($position !== false) {
                $path = substr($path, $position + strlen($marker));
                break;
            }
        }

        // اگر مسیر از قبل نسبی است (مثلاً 2/2026-06-02/a4c/media/...):
        // ابتدا تبدیل به مسیر مطلق کنیم و سپس بررسی کنیم
        $basePath = realpath(public_path('echos'));
        if ($basePath) {
            // اگر مسیر نسبی است، آن را نسبت به basePath ساخته و چک می‌کنیم
            $fullPath = $basePath . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $path);
            $absoluteCandidate = realpath($fullPath);

            if ($absoluteCandidate && $this->isPathInside($absoluteCandidate, $basePath)) {
                // تبدیل به مسیر نسبی نسبت به basePath
                $path = ltrim(str_replace('\\', '/', substr($absoluteCandidate, strlen($basePath))), '/');
            }
        }

        $path = ltrim($path, '/');
        if ($path === '' || str_contains($path, "\0") || str_contains($path, '../') || str_contains($path, '..\\')) {
            return null;
        }

        return $path;
    }

    private function looksLikePublicFilePath(string $path): bool  #ایا فایل معتبره؟ ایا مسیر فایل معتبره؟
    {
        $normalized = str_replace('\\', '/', $path);
        $hasDirectory = str_contains($normalized, '/');
        $hasKnownRoot = stripos($normalized, 'public/echos/') !== false
            || stripos($normalized, 'back/laravel/public/echos/') !== false
            || preg_match('#^[A-Za-z0-9_-]+/\d{4}-\d{2}-\d{2}/#', ltrim($normalized, '/'));
        $hasExtension = preg_match('/\.(jpg|jpeg|png|gif|webp|pdf|json|csv|txt|avi|mp4|mov|mkv|wmv)$/i', $normalized);

        return (bool) (($hasDirectory || $hasKnownRoot) && $hasExtension);
    }

    private function looksLikeFileList(?string $parentKey, array $items): bool  #یه ارایه از لیست فایل های عمومی؟
    {
        if (!$parentKey || !$this->isStringList($items)) {
            return false;
        }

        foreach ($items as $item) {
            if ($this->looksLikePublicFilePath($item)) {  #اگه مسیرش شبیه فایلای عمومی معتبر بود
                return true;
            }
        }

        return in_array($parentKey, ['plots', 'files', 'images'], true);  #یا اگه اسم فایل جز اینا بود
    }

    private function isStringList(array $items): bool  #چک میکنه ارایه یه لیستی از رشته باشه فقط
    {
        if (array_keys($items) !== range(0, count($items) - 1)) {
            return false;
        }

        foreach ($items as $item) {
            if (!is_string($item)) {
                return false;
            }
        }

        return true;
    }

    private function fileUrl(string $address): string  #ساخت url برای دانلود فایل
    {
        $encoded = implode('/', array_map('rawurlencode', explode('/', $address)));

        return url('/api/echo-history/file/' . $encoded);
    }

    private function publicFileExists(string $address): bool  #بررسی وجود فایل روی سرور
    {
        $basePath = realpath(public_path('echos'));
        if (!$basePath) {
            return false;
        }

        $candidate = realpath($basePath . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $address));

        return (bool) ($candidate && $this->isPathInside($candidate, $basePath) && file_exists($candidate));
    }

    private function isPathInside(string $path, string $basePath): bool  #چک میکنه ای این مسیر تو پوشه مدنظر هست یا نه
    {
        $path = rtrim(str_replace('\\', '/', $path), '/');
        $basePath = rtrim(str_replace('\\', '/', $basePath), '/');

        return $path === $basePath || str_starts_with($path, $basePath . '/');
    }
}
