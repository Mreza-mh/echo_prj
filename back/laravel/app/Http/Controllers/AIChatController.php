<?php

namespace App\Http\Controllers;

use App\Http\Requests\Ai\ChatRequest;
use App\Models\Service;
use App\Models\Expertise;
use App\Models\Staff;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Arr;
use Carbon\Carbon;
use App\Services\AppointmentService;

class AIChatController extends Controller
{
    private function debugLog($message, $data = null)
    {
        $timestamp = date('Y-m-d H:i:s');
        Log::channel('single')->info("[$timestamp] " . $message, $data ?? []);
    }

    private function assistantLog($message, $data = null)
    {
        $timestamp = date('Y-m-d H:i:s');
        Log::channel('single')->info("[$timestamp] " . $message, $data ?? []);
    }

    public function chat(ChatRequest $request)
    {
        $this->debugLog('--- NEW CHAT REQUEST ---', $request->all());

        $messages = array_values(array_filter(
            $request->input('messages', []),
            fn($m) => $m['role'] !== 'system'
        ));

        $user = auth('api')->user();
        $userInfo = $user
            ? "مشخصات کاربر وارد شده: نام: {$user->name}، شناسه (USER_LOGGED_IN_ID): {$user->id}"
            : 'کاربر فعلی وارد نشده است.';

        $systemPrompt = "
تو دستیار هوشمند رزرو نوبت پزشکی پلتفرم 'آکاری' (Acaree) هستی.
لحن: محترمانه، صمیمی و فقط به زبان فارسی.
وظیفه تو **فقط و فقط** کمک به رزرو نوبت جدید است. تو اجازه لغو، ویرایش یا تغییر نوبت‌ها را نداری.

قوانین حیاتی:
۱. فقط دیتابیس: اطلاعات را حدس نزن. فقط از خروجی ابزارها استفاده کن.
۲. شناسه USER_LOGGED_IN_ID مختص بیمار است. شناسه staff_id مختص پزشک است. هرگز این دو را جابجا نگیر.
۳. نمایش نوبت‌ها: لیست ساعت‌های خالی را با تگ [UI:SELECT_TIME] نمایش بده.
۴. در صورت خطای 'زمانبندی ثبت نشده'، به کاربر بگو برنامه کاری پزشک برای این روز پر است یا هنوز ثبت نشده است.

جریان گفتگو:
۱. جستجوی پزشک/تخصص (search_entities) -> نمایش با [UI:SELECT_STAFF]
۲. دریافت جزئیات و خدمات پزشک (get_staff_details) -> نمایش با [UI:SELECT_SERVICE]
۳. نمایش تقویم با [UI:SELECT_DATE]
۴. دریافت نوبت‌های خالی (get_available_slots) -> نمایش با [UI:SELECT_TIME]
۵. تایید نهایی: نمایش تگ [UI:CONFIRMATION] (منتظر تایید کاربر بمان و ابزاری صدا نزن).
۶. ثبت نوبت: پس از تایید کاربر، ابزار book_appointment را صدا بزن.
۷. برای پاسخ به سوالاتی مثل آدرس، شماره تلفن، بیمه‌ها، علائم بیماری یا تجهیزات کلینیک، حتماً از ابزار search_clinic_info استفاده کن و بر اساس خروجی آن به کاربر پاسخ محاوره‌ای بده. اطلاعات را از خودت حدس نزن.

فرمت پاسخ‌های UI:
- [UI:SELECT_STAFF:[{\"id\":1, \"name\":\"نام\", \"expertise\":\"تخصص\"}]]
- [UI:SELECT_SERVICE:[{\"id\":1, \"name\":\"نام خدمت\", \"price\":1000}]]
- [UI:SELECT_DATE:{\"staff_id\":1, \"service_id\":2}]
- [UI:SELECT_TIME:{\"date\":\"2024-01-20\", \"staff_id\":1, \"service_id\":2, \"slots\":[{\"start_time\":\"08:00\", \"end_time\":\"08:30\"}]}]
- [UI:CONFIRMATION:{\"staff_id\":1, \"service_id\":2, \"date\":\"2024-01-20\", \"time\":\"08:00\", \"staff_name\":\"نام پزشک\", \"service_name\":\"نام خدمت\"}]

اطلاعات محیطی:
- {$userInfo}
- تاریخ امروز: " . Carbon::now()->format('Y-m-d') . " (امروز " . Carbon::now()->format('l') . " است)";

        $tools = $this->tools();
        $round = 0;
        $maxRounds = 3;

        while ($round < $maxRounds) {
            $round++;
            try {
                $trimmedMessages = array_slice($messages, -8);
                $result = $this->callLLM($trimmedMessages, $systemPrompt, $tools);

                // بررسی وجود پیام در ساختار استاندارد
                if (!isset($result['choices'][0]['message'])) {

                    // بررسی اینکه آیا API خطایی برگردانده است یا خیر
                    $errorDetails = 'پاسخ نامعتبر یا ساختار ناشناخته';
                    if (isset($result['error'])) {
                        $errorDetails = is_array($result['error']) ? json_encode($result['error'], JSON_UNESCAPED_UNICODE) : $result['error'];
                    }

                    Log::error('AI Invalid Response: ' . json_encode($result, JSON_UNESCAPED_UNICODE));

                    return response()->json([
                        'error' => [
                            'message' => 'خطای API هوش مصنوعی: ' . $errorDetails,
                            'raw_response' => $result // اضافه کردن این بخش موقتاً برای اینکه در فرانت‌اند هم ارور را ببینید
                        ]
                    ], 400);
                }
            } catch (\Exception $e) {
                Log::error('AI Error: ' . $e->getMessage());
                return response()->json(['error' => ['message' => 'خطای ارتباط با هوش مصنوعی: ' . $e->getMessage()]], 500);
            }

            $message = $result['choices'][0]['message'];

            if (isset($message['content'])) {
                $content = preg_replace('/<think>[\s\S]*?<\/think>/', '', $message['content']);
                $content = preg_replace('/<think>[\s\S]*/', '', $content);
                $message['content'] = trim($content);
                $result['choices'][0]['message']['content'] = $message['content'];
            }

            if (empty($message['tool_calls'])) {
                if (empty($message['content']) && $round === 1) {
                    $result['choices'][0]['message']['content'] = 'چطور می‌توانم در رزرو نوبت به شما کمک کنم؟';
                }
                return $result;
            }

            $messages[] = $message;

            foreach ($message['tool_calls'] as $toolCall) {
                $toolName = $toolCall['function']['name'];
                $toolArgs = json_decode($toolCall['function']['arguments'], true);
                $output = $this->executeTool($toolName, $toolArgs);

                $messages[] = [
                    'role' => 'tool',
                    'tool_call_id' => $toolCall['id'],
                    'name' => $toolName,
                    'content' => json_encode($output, JSON_UNESCAPED_UNICODE),
                ];
            }
        }

        return response()->json(['message' => 'زمان گفتگو بیش از حد طولانی شد.'], 500);
    }

    private function callLLM($messages, $systemPrompt, $tools)
    {
        return config('services.ai.provider') === 'arvan'
            ? $this->callArvan($messages, $systemPrompt, $tools)
            : $this->callOpenRouter($messages, $systemPrompt, $tools);
    }


    private function callOpenRouter($messages, $systemPrompt, $tools)
    {
        foreach (config('services.ai.openrouter.models') as $model) {
            try {
                $payload = [
                    'model' => $model,
                    'messages' => array_merge(
                        [['role' => 'system', 'content' => $systemPrompt]],
                        $messages
                    ),
                    // 'tools' => $tools,
                    'temperature' => 0.2,
                    'max_tokens' => 600,
                ];

                $this->debugLog("Calling OpenRouter: Model={$model}", ['payload' => $payload]);

                $response = Http::timeout(20)->withHeaders([
                    'Authorization' => 'Bearer ' . config('services.ai.openrouter.key'),
                ])->post(config('services.ai.openrouter.base_url'), $payload);

                if ($response->successful()) {
                    $this->debugLog("OpenRouter Success: Model={$model}");
                    return $response->json();
                }

                $errorBody = $response->body();
                $this->debugLog("OpenRouter Failed: Model={$model}, Status={$response->status()}, Response={$errorBody}");

                Log::warning("OpenRouter Model {$model} failed: " . $errorBody);
                continue;
            } catch (\Throwable $e) {
                $this->debugLog("OpenRouter Throwable: Model={$model}, Error={$e->getMessage()}");
                Log::error('OpenRouter Error: ' . $e->getMessage());
                continue;
            }
        }

        throw new \Exception('تمامی مدل‌های هوش مصنوعی با خطا مواجه شدند.');
    }

    private function callArvan($messages, $systemPrompt, $tools)
    {
        $payload = [
            'model' => config('services.ai.arvan.model'),
            'messages' => array_merge(
                [['role' => 'system', 'content' => $systemPrompt]],
                $messages
            ),
            'tools' => $tools,
            'tool_choice' => 'auto',
            'temperature' => 0.2,
            'max_tokens' => 600,
        ];
        $this->debugLog('Calling Arvan: Model=' . config('services.ai.arvan.model'), ['payload' => $payload]);
        try {
            $response = Http::timeout(60)
                ->connectTimeout(5)
                ->withHeaders([
                    'Authorization' => 'Bearer ' . config('services.ai.arvan.key'),
                    'Content-Type' => 'application/json',
                ])
                ->post(config('services.ai.arvan.base_url'), $payload);

            if ($response->successful()) {
                $this->debugLog('Arvan Success');
                return $response->json();
            }

            $this->debugLog('Arvan Failed', [
                'status' => $response->status(),
                'body' => $response->body(),
                'url' => config('services.ai.arvan.base_url'),
            ]);
            // dd($response->status(), $response->body());


            $errorData = $response->json();
            $rawBody = $response->body(); // گرفتن متن خام پاسخ

            $errorMessage = $errorData['error']['message']
                ?? $errorData['message']
                ?? (empty($rawBody) ? 'خطای ناشناخته از سرویس هوش مصنوعی (Arvan)' : "ارور خام: " . $rawBody);


            throw new \Exception($errorMessage);

        } catch (\Throwable $e) {

            \Log::error('Arvan Exception', [
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString(),
            ]);

            throw $e;
        }
    }


    /* ================= TOOLS ================= */

    private function tools()
    {
        return [
            [
                'type' => 'function',
                'function' => [
                    'name' => 'search_entities',
                    'description' => 'جستجوی پزشک، تخصص یا خدمت پزشکی به زبان فارسی.',
                    'parameters' => [
                        'type' => 'object',
                        'properties' => [
                            'query' => ['type' => 'string']
                        ],
                        'required' => ['query'],
                    ],
                ],
            ],
            [
                'type' => 'function',
                'function' => [
                    'name' => 'get_staff_details',
                    'description' => 'دریافت خدمات یک پزشک بر اساس شناسه (staff_id).',
                    'parameters' => [
                        'type' => 'object',
                        'properties' => [
                            'staff_id' => ['type' => 'integer'],
                        ],
                        'required' => ['staff_id'],
                    ],
                ],
            ],
            [
                'type' => 'function',
                'function' => [
                    'name' => 'get_available_slots',
                    'description' => 'دریافت زمان‌های خالی بر اساس شناسه پزشک، خدمت و تاریخ.',
                    'parameters' => [
                        'type' => 'object',
                        'properties' => [
                            'staff_id' => ['type' => 'integer'],
                            'service_id' => ['type' => 'integer'],
                            'date' => ['type' => 'string', 'description' => 'YYYY-MM-DD'],
                        ],
                        'required' => ['staff_id', 'service_id', 'date'],
                    ],
                ],
            ],
            [
                'type' => 'function',
                'function' => [
                    'name' => 'book_appointment',
                    'description' => 'ثبت نهایی رزرو پس از تایید کاربر.',
                    'parameters' => [
                        'type' => 'object',
                        'properties' => [
                            'staff_id' => ['type' => 'integer'],
                            'service_id' => ['type' => 'integer'],
                            'date_of_turn' => ['type' => 'string'],
                            'start_time' => ['type' => 'string'],
                        ],
                        'required' => ['staff_id', 'service_id', 'date_of_turn', 'start_time'],
                    ],
                ],
            ],
            [
                'type' => 'function',
                'function' => [
                    'name' => 'search_clinic_info',
                    'description' => 'جستجوی اطلاعات کلینیک شامل: آدرس، شماره تماس، بیمه‌های طرف قرارداد، قوانین لغو نوبت، امکانات (مثل اکو فیلیپس) و بررسی علائم بیماری‌های قلبی.',
                    'parameters' => [
                        'type' => 'object',
                        'properties' => [
                            'query' => [
                                'type' => 'string',
                                'description' => 'سوال کاربر به صورت خلاصه برای جستجو در دیتابیس'
                            ]
                        ],
                        'required' => ['query'],
                    ],
                ],
            ],

        ];
    }

    private function executeTool($name, $args)
    {
        try {
            switch ($name) {
                case 'search_entities':
                    return $this->searchEntities($args);
                case 'get_staff_details':
                    return $this->getStaffDetails($args);
                case 'get_available_slots':
                    $result = app(AppointmentService::class)
                        ->getAvailableSlots(new \App\Http\Requests\Appointment\AvailableSlotsRequest($args));
                    return [
                        'slots' => $result['data'] ?? [],
                        'staff_id' => $args['staff_id'],
                        'service_id' => $args['service_id'],
                        'date' => $args['date']
                    ];
                case 'book_appointment':
                    if (!auth('api')->check()) {
                        return ['error' => 'ابتدا وارد حساب کاربری شوید.'];
                    }
                    return app(AppointmentService::class)
                        ->addAppointment(new \App\Http\Requests\Appointment\AppointmentCreateRequest([
                            'user_id' => auth('api')->id(),
                            'staff_id' => $args['staff_id'],
                            'service_id' => $args['service_id'],
                            'date_of_turn' => $args['date_of_turn'],
                            'start_time' => $args['start_time'],
                            'type' => 'Online',
                            'permissible_interference' => false,
                            'resource_ids' => [] // اگر منبع خاصی نیاز است اضافه شود
                        ]));
                case 'search_clinic_info':
                    return $this->searchClinicInfo($args);
                default:
                    return ['error' => 'ابزار یافت نشد'];
            }
        } catch (\Exception $e) {
            Log::error("Tool Error ({$name}): " . $e->getMessage());
            return ['error' => 'خطا در انجام عملیات.'];
        }
    }

    private function searchEntities($args)
    {
        $q = trim($args['query']);
        $searchTerms = ['دکتر', 'متخصص', 'آقای', 'خانم', 'پزشک', 'دکترای', 'جراح', 'کلینیک', 'بیمارستان', 'نوبت'];
        $cleanQ = trim(str_replace($searchTerms, '', $q));
        $words = array_filter(explode(' ', $cleanQ), fn($w) => mb_strlen($w) > 1);

        $expertises = cache()->remember('expertises_list', 3600, function () {
            return Expertise::all(['id', 'title', 'label']);
        });

        $englishExpertise = null;
        $queryWords = preg_split('/\s+/u', $cleanQ);

        foreach ($expertises as $exp) {
            $label = str_replace('‌', '', $exp->label);
            if ($cleanQ === $label || count(array_intersect($queryWords, preg_split('/\s+/u', $label))) > 0) {
                $englishExpertise = $exp->title;
                break;
            }
        }

        $staffQuery = Staff::query()
            ->select(['id', 'user_id', 'expertise_id'])
            ->with(['user:id,name', 'expertise:id,title,label']);

        if ($englishExpertise) {
            $staffQuery->whereHas('expertise', fn($query) => $query->where('title', 'like', "%$englishExpertise%"));
        } elseif (!empty($words)) {
            $staffQuery->where(function ($query) use ($words) {
                foreach ($words as $word) {
                    $query->orWhereHas('user', fn($q) => $q->where('name', 'like', "%$word%"))
                          ->orWhereHas('expertise', fn($q) => $q->where('title', 'like', "%$word%")->orWhere('label', 'like', "%$word%"));
                }
            });
        } else {
            $staffQuery->limit(10); // خروجی پیش‌فرض در صورت خالی بودن
        }

        $staff = $staffQuery->take(10)->get()->map(fn($s) => [
            'type' => 'staff',
            'id' => $s->id,
            'name' => $s->user->name ?? 'بدون نام',
            'expertise' => $s->expertise ? ($s->expertise->label ?: $s->expertise->title) : 'پزشک عمومی',
        ]);

        return ['results' => $staff->toArray()];
    }

    private function getStaffDetails($args)
    {
        $staff = Staff::with(['user:id,name', 'expertise:id,title,label'])->find($args['staff_id']);
        if (!$staff) return ['error' => 'پزشک پیدا نشد'];

        // استفاده مستقیم از دیتابیس برای افزایش سرعت به جای استفاده از مپینگ سنگین
        $services = Service::query()
            ->select('services.id', 'services.title', 'services.price')
            ->join('appointments', 'appointments.service_id', '=', 'services.id')
            ->where('appointments.staff_id', $staff->id)
            ->distinct()
            ->get();

        return [
            'id' => $staff->id,
            'name' => $staff->user->name ?? 'بدون نام',
            'expertise' => $staff->expertise ? ($staff->expertise->label ?: $staff->expertise->title) : 'پزشک عمومی',
            'services' => $services->toArray(),
        ];
    }

    private function searchClinicInfo($args)
    {
        $query = $args['query'] ?? '';

        try {
            // ارسال درخواست به میکروسرویس پایتون که قبلا نوشتید
            $response = Http::timeout(10)->post('http://127.0.0.1:8000/search-faiss', [
                'sentence' => $query
            ]);

            if ($response->successful()) {
                $data = $response->json();

                // استخراج فقط متن جملات برای ارسال به LLM تا توکن کمتری مصرف شود
                $sentences = [];
                if (!empty($data['results'])) {
                    foreach ($data['results'] as $result) {
                        $sentences[] = $result['sentence'];
                    }
                }

                if (empty($sentences)) {
                    return ['message' => 'اطلاعاتی در این باره یافت نشد. به کاربر بگو با پذیرش تماس بگیرد.'];
                }

                return [
                    'retrieved_information' => $sentences,
                    'instruction' => 'با استفاده از اطلاعات بالا، یک پاسخ طبیعی، محترمانه و کوتاه به کاربر بده.'
                ];
            }

            return ['error' => 'ارتباط با سرویس جستجوی اطلاعات قطع است.'];

        } catch (\Exception $e) {
            Log::error('Qdrant Search Error: ' . $e->getMessage());
            return ['error' => 'خطا در جستجوی اطلاعات کلینیک.'];
        }
    }



}
