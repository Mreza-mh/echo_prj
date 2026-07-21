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
        $patientId = $this->resolvePatientId($patient_id);
        $document = $this->findPatientDocument($patientId);

        if (!$document) {
            throw new ErrorException('Echo history not found');
        }

        $data = $this->normalizeMongoValue($document);
        $data['patient_id'] = (string) ($data['_id'] ?? $patientId);
        $data = $this->appendFileLinks($data);

        return [
            'message' => 'Echo history loaded successfully',
            'data' => $data,
        ];
    }

    public function getFile($address): string
    {
        $basePath = realpath(public_path('echos'));
        if (!$basePath) {
            throw new ErrorException('Echo public directory not found');
        }

        $normalizedAddress = $this->normalizeFileAddress($address);
        if (!$normalizedAddress) {
            throw new ErrorException('Invalid file path');
        }

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
        $candidates = [$patientId];
        if (ctype_digit($patientId)) {
            $candidates[] = (int) $patientId;
        }

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
            $cursor = $this->manager()->executeQuery($this->collectionNamespace(), $query);

            foreach ($cursor as $document) {
                return $document;
            }
        } catch (\Throwable $exception) {
            throw new ErrorException('MongoDB connection failed: ' . $exception->getMessage());
        }

        return null;
    }

    private function normalizeMongoValue($value)
    {
        if ($value instanceof \Illuminate\Support\Collection) {
            $value = $value->all();
        }

        if ($value instanceof \MongoDB\Model\BSONDocument || $value instanceof \MongoDB\Model\BSONArray) {
            $value = $value->getArrayCopy();
        }

        if ($value instanceof \MongoDB\BSON\ObjectId) {
            return (string) $value;
        }

        if ($value instanceof \MongoDB\BSON\UTCDateTime) {
            return $value->toDateTime()->format(DATE_ATOM);
        }

        if (is_object($value)) {
            $value = get_object_vars($value);
        }

        if (is_array($value)) {
            foreach ($value as $key => $item) {
                $value[$key] = $this->normalizeMongoValue($item);
            }
        }

        return $value;
    }

    private function appendFileLinks($value, ?string $parentKey = null)
    {
        if (!is_array($value)) {
            return $value;
        }

        foreach ($value as $key => $item) {
            if (is_array($item)) {
                $value[$key] = $this->appendFileLinks($item, is_string($key) ? $key : $parentKey);
                continue;
            }

            if (!is_string($item) || !$this->looksLikePublicFilePath($item)) {
                continue;
            }

            $address = $this->normalizeFileAddress($item);
            if (!$address) {
                continue;
            }

            if (is_string($key)) {
                $value[$key . '_address'] = $address;
                $value[$key . '_url'] = $this->fileUrl($address);
                $value[$key . '_exists'] = $this->publicFileExists($address);
            }
        }

        if ($this->isStringList($value) && $this->looksLikeFileList($parentKey, $value)) {
            return [
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

    private function normalizeFileAddress(?string $path): ?string
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

    private function looksLikePublicFilePath(string $path): bool
    {
        $normalized = str_replace('\\', '/', $path);
        $hasDirectory = str_contains($normalized, '/');
        $hasKnownRoot = stripos($normalized, 'public/echos/') !== false
            || stripos($normalized, 'back/laravel/public/echos/') !== false
            || preg_match('#^[A-Za-z0-9_-]+/\d{4}-\d{2}-\d{2}/#', ltrim($normalized, '/'));
        $hasExtension = preg_match('/\.(jpg|jpeg|png|gif|webp|pdf|json|csv|txt|avi|mp4|mov|mkv|wmv)$/i', $normalized);

        return (bool) (($hasDirectory || $hasKnownRoot) && $hasExtension);
    }

    private function looksLikeFileList(?string $parentKey, array $items): bool
    {
        if (!$parentKey || !$this->isStringList($items)) {
            return false;
        }

        foreach ($items as $item) {
            if ($this->looksLikePublicFilePath($item)) {
                return true;
            }
        }

        return in_array($parentKey, ['plots', 'files', 'images'], true);
    }

    private function isStringList(array $items): bool
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

    private function fileUrl(string $address): string
    {
        $encoded = implode('/', array_map('rawurlencode', explode('/', $address)));

        return '/api/echo-history/file/' . $encoded;
    }

    private function publicFileExists(string $address): bool
    {
        $basePath = realpath(public_path('echos'));
        if (!$basePath) {
            return false;
        }

        $candidate = realpath($basePath . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $address));

        return (bool) ($candidate && $this->isPathInside($candidate, $basePath) && file_exists($candidate));
    }

    private function isPathInside(string $path, string $basePath): bool
    {
        $path = rtrim(str_replace('\\', '/', $path), '/');
        $basePath = rtrim(str_replace('\\', '/', $basePath), '/');

        return $path === $basePath || str_starts_with($path, $basePath . '/');
    }
}
