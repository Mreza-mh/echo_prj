<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;
use MongoDB\Client as MongoClient;

class PatientReportController extends Controller
{
    private function getMongoCollection()
    {
        $mongoUri = env('ECHO_MONGO_URI', 'mongodb://localhost:27017/');
        $dbName = env('ECHO_MONGO_DB', 'echo_pipeline');
        $collectionName = env('ECHO_MONGO_COLLECTION', 'patients');

        $client = new MongoClient($mongoUri);
        return $client->selectCollection($dbName, $collectionName); #hjwhg fi l,k', , ;hg;ak
    }

    /**
     * دریافت لیست تمام ویزیت‌های یک بیمار
     */
    public function getPatientVisits($patientId)
    {
        try {
            $collection = $this->getMongoCollection();
            $patient = $collection->findOne(['_id' => $patientId]); #nvdhtj fdlhv hc l,k',

            if (!$patient) {
                return response()->json([
                    'success' => false,
                    'message' => 'بیمار یافت نشد'
                ], 404);
            }

            $visits = [];
            if (isset($patient['visits'])) {
                foreach ($patient['visits'] as $date => $visitData) {
                    $visits[] = [
                        'date' => $date,
                        'views_count' => count($visitData),
                        'has_final_report' => $this->hasFinalReport($visitData)  #ایا گزارش نهایی llm رو داره؟
                    ];
                }
            }

            return response()->json([
                'success' => true,
                'patient_info' => $patient['patient_info'] ?? [],
                'visits' => $visits
            ]);

        } catch (\Exception $e) {
            Log::error('Error fetching patient visits: ' . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'خطا در دریافت اطلاعات بیمار'
            ], 500);
        }
    }

    /**
     * دریافت گزارش نهایی یک ویزیت خاص
     */
    public function getPatientReport($patientId, $visitDate)
    {
        try {
            $collection = $this->getMongoCollection();
            $patient = $collection->findOne(['_id' => $patientId]); #بیمارو از مونگو میخونه

            if (!$patient) {
                return response()->json([
                    'success' => false,
                    'message' => 'بیمار یافت نشد'
                ], 404);
            }

            $visitData = $patient['visits'][$visitDate] ?? null; #تاریخی که مدنظرشه

            if (!$visitData) {
                return response()->json([
                    'success' => false,
                    'message' => 'ویزیت یافت نشد'
                ], 404);
            }

            // جستجوی گزارش نهایی LLM
            $llmReport = null;
            $fuzzyReport = null;
            $measurements = [];

            foreach ($visitData as $item) {
                if (isset($item['type'])) {
                    if ($item['type'] === 'llm_final_report') { #گزارشی که llmتولید کرده رو میگیره
                        $llmReport = $item;
                    } elseif ($item['type'] === 'fuzzy_summary') {  #گزارشی که از سیستم استنتاج فازی اومده رو میگیره
                        $fuzzyReport = $item;
                    } else {
                        // جمع‌آوری اندازه‌گیری‌ها از نماهای مختلف
                        if (isset($item['measurements'])) {
                            $measurements = array_merge($measurements, $item['measurements']);  #اندازه هایی که از پردازش فیلم اکو اومده میگیره  
                        }
                    }
                }
            }

            return response()->json([
                'success' => true,
                'patient_info' => $patient['patient_info'] ?? [],
                'visit_date' => $visitDate,
                'llm_report' => $llmReport,
                'fuzzy_report' => $fuzzyReport,
                'measurements' => $measurements
            ]);

        } catch (\Exception $e) {
            Log::error('Error fetching patient report: ' . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'خطا در دریافت گزارش'
            ], 500);
        }
    }

    /**
     * دریافت متن گزارش (برای استفاده در API)
     */
    public function getReportText($patientId, $visitDate)
    {
        try {
            $collection = $this->getMongoCollection();
            $patient = $collection->findOne(['_id' => $patientId]);

            if (!$patient) {
                return response()->json([
                    'success' => false,
                    'message' => 'بیمار یافت نشد'
                ], 404);
            }

            $visitData = $patient['visits'][$visitDate] ?? null;

            if (!$visitData) {
                return response()->json([
                    'success' => false,
                    'message' => 'ویزیت یافت نشد'
                ], 404);
            }

            foreach ($visitData as $item) {
                if (isset($item['type']) && $item['type'] === 'llm_final_report') {
                    return response()->json([
                        'success' => true,
                        'report_text' => $item['report_text'] ?? '',
                        'generated_at' => $item['generated_at'] ?? null,
                        'files' => $item['files'] ?? []
                    ]);
                }
            }

            return response()->json([
                'success' => false,
                'message' => 'گزارش نهایی هنوز تولید نشده است'
            ], 404);

        } catch (\Exception $e) {
            Log::error('Error getting report text: ' . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'خطا در دریافت متن گزارش'
            ], 500);
        }
    }

    /**
     * بررسی اینکه آیا گزارش نهایی وجود دارد
     */
    private function hasFinalReport($visitData)
    {
        foreach ($visitData as $item) {
            if (isset($item['type']) && $item['type'] === 'llm_final_report') {
                return true;
            }
        }
        return false;
    }

    /**
     * دریافت خلاصه وضعیت بیمار (برای داشبورد)
     */
    public function getPatientSummary($patientId)
    {
        try {
            $collection = $this->getMongoCollection();
            $patient = $collection->findOne(['_id' => $patientId]);

            if (!$patient) {
                return response()->json([
                    'success' => false,
                    'message' => 'بیمار یافت نشد'
                ], 404);
            }

            $latestVisit = null;
            $latestDate = null;
            $totalVisits = 0;

            if (isset($patient['visits'])) {
                $dates = array_keys((array) $patient['visits']);
                rsort($dates); // مرتب‌سازی نزولی

                $totalVisits = count($dates);

                if (count($dates) > 0) {
                    $latestDate = $dates[0];
                    $latestVisit = $patient['visits'][$latestDate];
                }
            }

            // استخراج آخرین امتیاز ریسک
            $latestRiskScore = null;
            $latestSeverity = null;

            if ($latestVisit) {
                foreach ($latestVisit as $item) {
                    if (isset($item['type']) && $item['type'] === 'fuzzy_summary') {
                        $latestRiskScore = $item['result']['score'] ?? null;
                        $latestSeverity = $item['result']['category'] ?? null;
                        break;
                    }
                }
            }

            return response()->json([
                'success' => true,
                'patient_info' => $patient['patient_info'] ?? [],
                'summary' => [
                    'total_visits' => $totalVisits,
                    'latest_visit_date' => $latestDate,
                    'latest_risk_score' => $latestRiskScore,
                    'latest_severity' => $latestSeverity,
                    'has_latest_report' => $latestVisit ? $this->hasFinalReport($latestVisit) : false
                ]
            ]);

        } catch (\Exception $e) {
            Log::error('Error getting patient summary: ' . $e->getMessage());
            return response()->json([
                'success' => false,
                'message' => 'خطا در دریافت خلاصه وضعیت بیمار'
            ], 500);
        }
    }
}
