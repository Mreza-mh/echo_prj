<?php


namespace App\Http\Controllers;

use App\Enums\UserRole;
use App\Http\Requests\Ai\ChatRequest;
use App\Models\Service;
use App\Models\Expertise;
use App\Models\Staff;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Carbon\Carbon;
use App\Services\AppointmentService;
use Illuminate\Support\Facades\Auth;


class AIChatController extends Controller
{
    private $pythonServiceUrl = 'http://127.0.0.1:9000';

    protected $appointmentService;

    public function __construct(AppointmentService $appointmentService)
    {
        $this->appointmentService = $appointmentService;
    }

    public function chat(ChatRequest $request)
{
    // ۱. دریافت پیام‌ها
    $messages = array_values(array_filter(
        $request->input('messages', []),
        fn($m) => $m['role'] !== 'system'
    ));

    // ۲. دریافت وضعیت فعلی اسلات‌ها
    $previousState = $request->input('current_slots', [
        'doctor_name' => null,
        'service_name' => null,
        'date' => null,
        'start_time' => null
    ]);

    $lastUserMessage = end($messages)['content'] ?? '';

    if (empty($lastUserMessage)) {
        return response()->json(['message' => 'پیام نمی‌تواند خالی باشد.'], 400);
    }

    try {
        // --- بخش اصلاح شده (Logic Logic) ---

        // بررسی اینکه آیا کاربر در حال طی کردن مراحل رزرو است؟
        // اگر نام دکتر یا خدمت از قبل مشخص شده، یعنی کاربر در "جریان رزرو" قرار دارد.
        $isInBookingProcess = !empty($previousState['doctor_name']) || !empty($previousState['service_name']);

        if ($isInBookingProcess) {
            // بدون توجه به خروجی Router، به نوبت‌دهی ادامه بده
            return $this->handleAppointmentIntent($messages, $lastUserMessage, $previousState);
        }

        // اگر کاربر تازه مکالمه را شروع کرده یا هیچ اسلاتی پر نشده، حالا مسیریابی کن
        $routeResponse = Http::timeout(20)->post("{$this->pythonServiceUrl}/route", [
            'sentence' => $lastUserMessage
        ]);

        $routeData = $routeResponse->json();
        $intent = $routeData['intent'] ?? 'appointment';
        $score = $routeData['score'] ?? 0;

        // سخت‌گیری بیشتر: اگر امتیاز پشتیبانی کم بود، باز هم ببرش سمت نوبت‌دهی
        if ($intent === 'support' && $score > 0.8) {
            return $this->handleSupportIntent($messages, $lastUserMessage);
        }

        return $this->handleAppointmentIntent($messages, $lastUserMessage, $previousState);

    } catch (\Exception $e) {
        Log::error('Routing Error: ' . $e->getMessage());
        return response()->json(['error' => ['message' => 'خطا در پردازش درخواست شما.']], 500);
    }
} 
    
    /**
     * مدیریت سناریوی پشتیبانی و سوالات عمومی (کاملاً بدون ابزار و سبک)
     */
    private function handleSupportIntent($messages, $lastUserMessage)
    {
        // ۱. واکشی اطلاعات متنی مرتبط از Qdrant (RAG)
        $qdrantResponse = Http::timeout(20)->post("{$this->pythonServiceUrl}/search-faiss", [
            'sentence' => $lastUserMessage
        ]);

        $retrievedTexts = [];
        if ($qdrantResponse->successful() && isset($qdrantResponse->json()['results'])) {
            foreach ($qdrantResponse->json()['results'] as $row) {
                $retrievedTexts[] = $row['sentence'];
            }
        }

        if (empty($retrievedTexts)) {
            return response()->json([
                'choices' => [[
                    'message' => [
                        'role' => 'assistant',
                        'content' => 'متاسفانه اطلاعاتی در این زمینه پیدا نکردم. لطفاً با شماره تلفن ۳۳۳۳۳۳۳۶ تماس بگیرید.'
                    ]
                ]]
            ]);
        }

        // ۲. ساخت پرامپت به شدت مینی‌مال فقط برای پاسخ متنی
        $systemPrompt = 'تو بخش پشتیبانی و روابط عمومی کلینیک پزشکی آکاری هستی.
با استفاده از اطلاعات مستند زیر، به سوال کاربر پاسخ کوتاه، محترمانه و صمیمی به زبان فارسی بده.
حق نداری اطلاعاتی خارج از متن زیر ارائه کنی یا حدس بزنی.

مستندات کلینیک:
' . implode("\n", $retrievedTexts);

        // ارسال به مدل بدون تعریف هیچ نوع ابزاری (کاهش شدید حجم توکن)
        return $this->callLLMRaw($messages, $systemPrompt);
    }

    /**
     * مدیریت سناریوی نوبت‌دهی و استخراج فیلدها (Slot Filling)
     */
    private function handleAppointmentIntent($messages, $lastUserMessage, $previousState = [])
    {
        $user = Auth::user();

        // تبدیل وضعیت قبلی به متنی برای مدل (حافظه فشرده)
        $stateContext = 'وضعیت فعلی رزرو: ' . json_encode($previousState, JSON_UNESCAPED_UNICODE);
        $today = now()->format('Y-m-d');
        $dayOfWeek = now()->dayName;

        $systemPrompt = "تو یک استخراج‌کننده فرم هوشمند هستی.
    {$stateContext}
    وظیفه داری با توجه به آخرین پیام کاربر، اطلاعات را بروزرسانی کنی.
    فقط JSON برگردان شامل کلیدهای: doctor_name, service_name, date, start_time.
    اگر فیلدی تغییر نکرده، همان مقدار قبلی را برگردان. ساعت را به فرمت HH:mm (انگلیسی) تبدیل کن.
    امروز {$dayOfWeek} تاریخ {$today} است.
اگر کاربر از کلمات نسبی مثل 'فردا' استفاده کرد، تو عیناً کلمه 'فردا' را در فیلد date بنویس و خودت تبدیل نکن.";

        // برای بهینه‌سازی، فقط پیام آخر کاربر را همراه با وضعیت قبلی به مدل می‌دهیم
        $aiResponse = $this->callLLMRaw([['role' => 'user', 'content' => $lastUserMessage]], $systemPrompt);
        $aiContent = preg_replace('/<think>[\s\S]*?<\/think>/', '', $aiResponse['choices'][0]['message']['content'] ?? '');

        if (preg_match('/\{[\s\S]*\}/', $aiContent, $matches)) {
            $jsonData = json_decode($matches[0], true);
        } else {
            $jsonData = $previousState; // فال‌بک به وضعیت قبلی در صورت خطای مدل
        }

        // اطمینان از وجود تمام کلیدها
        $jsonData = array_merge([
            'doctor_name' => null, 'service_name' => null, 'date' => null, 'start_time' => null
        ], $jsonData);

        if ($user) {
            $jsonData['user_id'] = $user->id;
        }

        return $this->processAppointmentBusinessLogic($jsonData, $lastUserMessage, $messages);
    }

    /**
     * منطق تجاری نوبت‌دهی بر اساس فیلدهای استخراج شده
     */
    private function processAppointmentBusinessLogic($slots, $lastUserMessage, $messages)
    {
        // ۱. دریافت وضعیت قبلی از درخواستی که به کنترلر اومده
        // (فرض می‌کنیم اسم فیلد رو در ریکوئست گذاشتی current_slots)
        $previousSlots = request()->input('current_slots', []);

        // ۲. ادغام اسلات‌های جدید با قبلی (Merge)
        // با این کار، اگر کاربر قبلاً گفته "دکتر احمدی" و الان فقط بگه "اکو"،
        // مقدار دکتر احمدی از بین نمی‌ره.
        $slots = array_merge([
            'doctor_name' => null,
            'service_name' => null,
            'date' => null,
            'start_time' => null,
            'user_id' => auth('api')->id()
        ], $previousSlots, array_filter($slots));


        $serviceHelperText = '';
        $staffHelperText = '';
        $slotsText = ''; // برای ذخیره تایم‌های خالی
// ۱. شناسایی پزشک
        $staffFound = null;
        if (!empty($slots['doctor_name'])) {
            $cleanName = trim(str_replace(['دکتر', 'متخصص'], '', $slots['doctor_name']));

            // پیدا کردن استفی که کاربرش نام مشابه دارد و نقش آن دکتر است
            $staffFound = Staff::whereHas('user', function ($q) use ($cleanName) {
                $q->where('role', UserRole::doctor->value)->where('name', 'like', "%{$cleanName}%");
            })->first();

            if ($staffFound) {
                $slots['doctor_name'] = $staffFound->user->name;
            } else {
                // اگر اسم اشتباه بود، لیست تمام کاربران با نقش دکتر را می‌گیریم
                $allDoctors = \App\Models\User::where('role', UserRole::doctor->value)->pluck('name')->toArray();

                $staffHelperText = "پزشکی با نام '{$slots['doctor_name']}' پیدا نشد. لیست پزشکان معتبر ما: [" . implode('، ', $allDoctors) . ']';
                $slots['doctor_name'] = null;
            }
        } else {
            // اگر کاربر هنوز نام پزشک را نگفته، لیست دکترا را از دیتابیس بکش
            $allDoctors = \App\Models\User::where('role', 'doctor')->pluck('name')->toArray();
            if (!empty($allDoctors)) {
                $staffHelperText = 'کاربر هنوز نام پزشک را نگفته است. حتماً لیست این پزشکان را به او نشان بده تا یکی را انتخاب کند: [' . implode('، ', $allDoctors) . ']';
            }
        }

        // ۲. شناسایی خدمت
        $serviceFound = null;
        if (!empty($slots['service_name'])) {
            // پاکسازی نام خدمت برای جستجوی بهتر
            $searchTerm = trim($slots['service_name']);
            
            $serviceFound = \App\Models\Service::where('title', 'like', "%{$searchTerm}%")->first();

            if ($serviceFound) {
                $slots['service_name'] = $serviceFound->title;
                // نکته مهم: اینجا باید مقدار helper رو خالی کنی که هوش مصنوعی گیج نشه
                $serviceHelperText = "خدمت انتخاب شده: {$serviceFound->title}"; 
            } else {
                $allServices = \App\Models\Service::pluck('title')->toArray();
                $serviceHelperText = 'کاربر خدمتی گفت که در لیست نیست. لیست دقیق خدمات ما: [' . implode('، ', $allServices) . ']. از کاربر بخواه دقیقاً یکی از این موارد را انتخاب کند.';
                $slots['service_name'] = null; // ریست کن تا دوباره بپرسه
            }
        }

        // // ۲. شناسایی خدمت (طبق کد قبلی شما)
        // // ۲. شناسایی خدمت (طبق کد قبلی شما با یک اصلاح کوچک)
        // $serviceFound = null;
        // if (!empty($slots['service_name'])) {
        //     $serviceFound = \App\Models\Service::where('title', 'like', "%{$slots['service_name']}%")->first();
        //     if ($serviceFound) {
        //         $slots['service_name'] = $serviceFound->title;
        //     } else {
        //         $allServices = \App\Models\Service::pluck('title')->toArray();
        //         $serviceHelperText = 'خدمت انتخاب شده نامعتبر است. لیست خدمات واقعی ما: [' . implode('، ', $allServices) . ']';
        //         $slots['service_name'] = null;
        //     }
        // } else {
        //     // --- این بخش اضافه شد: اگر کاربر هنوز خدمتی انتخاب نکرده، لیست رو براش بفرست ---
        //     $allServices = \App\Models\Service::pluck('title')->toArray();
        //     if (!empty($allServices)) {
        //         $serviceHelperText = 'کاربر هنوز خدمتی انتخاب نکرده است. حتماً این لیست دقیق را به کاربر نشان بده تا انتخاب کند: [' . implode('، ', $allServices) . ']';
        //     }
        // }

        // ۳. بررسی تاریخ و استخراج زمان‌های خالی
        // if ($staffFound && $serviceFound && !empty($slots['date'])) {
        //     // تبدیل تاریخ "فردا" یا "شنبه" به تاریخ میلادی استاندارد Y-m-d
        //     $standardDate = $this->convertRelativeDateToStandard($slots['date']);

        //     // ساخت یک Request فیک برای پاس دادن به سرویس نوبت‌دهی شما
        //     $availableSlotsRequest = new \App\Http\Requests\Appointment\AvailableSlotsRequest([
        //         'staff_id' => $staffFound->id,
        //         'service_id' => $serviceFound->id,
        //         'date' => $standardDate
        //     ]);

        //     try {
        //         $availableData = $this->appointmentService->getAvailableSlots($availableSlotsRequest);
        //         $availableSlots = $availableData['data'];

        //         if (empty($availableSlots)) {
        //             $slotsText = "متاسفانه برای تاریخ {$slots['date']} هیچ زمان خالی پیدا نشد. لطفاً روز دیگری را بپرسید.";
        //             $slots['date'] = null; // ریست تاریخ برای پرسش مجدد
        //         } else {
        //             // تبدیل لیست زمان‌ها به یک رشته متنی برای هوش مصنوعی
        //             $times = collect($availableSlots)->map(fn($s) => $s['start_time'])->take(8)->implode('، ');
        //             $slotsText = "زمان‌های خالی پیدا شده برای {$slots['date']}: [{$times}]. از کاربر بخواه یکی را انتخاب کند.";
        //         }
        //     } catch (\Exception $e) {
        //         $slotsText = 'خطا در استخراج زمان‌های خالی.';
        //     }
        // }

        // ۳. بررسی تاریخ و استخراج زمان‌های خالی
        if ($staffFound && $serviceFound) {
            if (empty($slots['date'])) {
                // اگر تاریخ نداریم، از کاربر بخواهیم تاریخ بدهد
                $slotsText = "هنوز تاریخی انتخاب نشده است. از کاربر بخواه برای چه روزی (مثلاً فردا، شنبه یا ...) نوبت می‌خواهد.";
            } else {
                $standardDate = $this->convertRelativeDateToStandard($slots['date']);
                
                $availableSlotsRequest = new \App\Http\Requests\Appointment\AvailableSlotsRequest([
                    'staff_id' => $staffFound->id,
                    'service_id' => $serviceFound->id,
                    'date' => $standardDate
                ]);

                try {
                    $availableData = $this->appointmentService->getAvailableSlots($availableSlotsRequest);
                    $availableSlots = $availableData['data'] ?? [];

                    if (empty($availableSlots)) {
                        $slotsText = "متاسفانه برای تاریخ {$slots['date']} هیچ زمان خالی پیدا نشد. از کاربر بخواه روز دیگری را انتخاب کند.";
                        $slots['date'] = null; // ریست کردن تاریخ برای پرسش مجدد
                    } else {
                        $times = collect($availableSlots)->map(fn($s) => $s['start_time'])->take(8)->implode('، ');
                        // مقدار واقعی که باید به هوش مصنوعی برسد
                        $slotsText = "زمان‌های خالی در تاریخ {$slots['date']}: [{$times}]. حتماً این زمان‌ها را به کاربر نشان بده تا یکی را انتخاب کند.";
                    }
                } catch (\Exception $e) {
                    $slotsText = "خطا در دریافت نوبت‌ها: " . $e->getMessage();
                }
            }
        }
        // ۴. بررسی وجود ساعت و ثبت نهایی
        if ($staffFound && $serviceFound && !empty($slots['date']) && !empty($slots['start_time'])) {

            $standardDate = $this->convertRelativeDateToStandard($slots['date']);
            $user = auth('api')->user();

            // ایجاد ریکوئست برای متد addAppointment موجود در سرویس شما
            $appointmentRequest = new \App\Http\Requests\Appointment\AppointmentCreateRequest([
                'user_id' => $user->id,
                'staff_id' => $staffFound->id,
                'service_id' => $serviceFound->id,
                'date_of_turn' => $standardDate,
                'start_time' => $slots['start_time'],
                'type' => 'Online',
                'permissible_interference' => false // طبق منطق شما
            ]);


            try {
                // فراخوانی متد ثبت از AppointmentService
                $result = $this->appointmentService->addAppointment($appointmentRequest);

                $finalPrompt = "کاربر نوبت خودش رو برای ساعت {$slots['start_time']} روز {$slots['date']} با موفقیت ثبت کرد.
                            یک پیام تایید خیلی خوشحال‌کننده و کوتاه بهش بده و بگو که منتظرش هستیم.";

                return $this->callLLMRaw($messages, $finalPrompt);

            } catch (\Exception $e) {
                Log::error('Appointment Booking Error: ' . $e->getMessage());
                $errorPrompt = 'متاسفانه مشکلی در ثبت نهایی پیش اومد: ' . $e->getMessage() . '. محترمانه عذرخواهی کن.';
                return $this->callLLMRaw($messages, $errorPrompt);
            }
        }

        // 5. ساخت پرامپت نهایی
        $currentStatus = 'اطلاعات استخراج شده: ' . json_encode($slots, JSON_UNESCAPED_UNICODE);

        $finalPrompt = "تو دستیار رزرو نوبت کلینیک هستی.
وضعیت: {$currentStatus}
{$staffHelperText}
{$serviceHelperText}
{$slotsText}

قوانین:
1. اگر لیست زمان‌های خالی (slotsText) وجود دارد، آن‌ها را به کاربر نمایش بده و بگو یکی را انتخاب کند.
2. اگر زمان‌های خالی وجود ندارد، محترمانه بگو وقت‌ها پر است.
3. پاسخ صمیمی، بسیار کوتاه و به زبان فارسی باشد.";

        $aiFinalResponse = $this->callLLMRaw($messages, $finalPrompt);

        return response()->json([
            'choices' => $aiFinalResponse['choices'],
            'current_slots' => $slots // فرستادن حافظه آپدیت شده به کاربر
        ]);
    }

    /**
     * تابع کمکی برای تبدیل "فردا"، "پس‌فردا" یا روزهای هفته به تاریخ استاندارد
     */
    private function convertRelativeDateToStandard($relativeDate)
    {
        $date = now();

        if (str_contains($relativeDate, 'فردا')){
            $date->addDay(1);     
        }
        if (str_contains($relativeDate, 'پس‌فردا')) $date->addDays(2);

        // نگاشت روزهای هفته (ساده شده)
        $days = [
            'شنبه' => Carbon::SATURDAY, 'یکشنبه' => Carbon::SUNDAY, 'دوشنبه' => Carbon::MONDAY,
            'سه‌شنبه' => Carbon::TUESDAY, 'چهارشنبه' => Carbon::WEDNESDAY, 'پنج‌شنبه' => Carbon::THURSDAY, 'جمعه' => Carbon::FRIDAY
        ];

        foreach ($days as $dayName => $dayConstant) {
            if (str_contains($relativeDate, $dayName)) {
                $date->next($dayConstant);
                break;
            }
        }

        return $date->format('Y-m-d');
    }    /**
     * متد عمومی و سبک برای ارتباط با مدل‌های زبانی (بدون ساختار پیچیده Tools)
     */
    private function callLLMRaw($messages, $systemPrompt)
    {
        $provider = config('services.ai.provider');
        $model = $provider === 'arvan'
            ? config('services.ai.arvan.model')
            : head(config('services.ai.openrouter.models'));

        $baseUrl = $provider === 'arvan'
            ? config('services.ai.arvan.base_url')
            : config('services.ai.openrouter.base_url');

        $apiKey = $provider === 'arvan'
            ? config('services.ai.arvan.key')
            : config('services.ai.openrouter.key');

        $payload = [
            'model' => $model,
            'messages' => array_merge(
                [['role' => 'system', 'content' => $systemPrompt]],
                $messages
            ),
            'temperature' => 0.2,
            'max_tokens' => 400, // کاهش تعداد توکن خروجی برای بهینه‌سازی سرعت
        ];

        $response = Http::timeout(20)->connectTimeout(10)->withHeaders([
            'Authorization' => 'Bearer ' . $apiKey,
            'Content-Type' => 'application/json',
        ])->post($baseUrl, $payload);

        if ($response->successful()) {
            return $response->json();
        }

        throw new \Exception('خطا در برقراری ارتباط با LLM: ' . $response->body());
    }

    private function generateConversationFallback($messages)
    {
        return [
            'choices' => [[
                'message' => [
                    'role' => 'assistant',
                    'content' => 'من آماده رزرو نوبت شما هستم. نام پزشک یا تخصص مورد نظرتان را بفرمایید؟'
                ]
            ]]
        ];
    }
}
//
//namespace App\Http\Controllers;
//
//use App\Http\Requests\Ai\ChatRequest;
//use App\Models\Service;
//use App\Models\Expertise;
//use App\Models\Staff;
//use Illuminate\Http\Request;
//use Illuminate\Support\Facades\Http;
//use Illuminate\Support\Facades\Log;
//use Illuminate\Support\Arr;
//use Carbon\Carbon;
//use App\Services\AppointmentService;
//
//class AIChatController extends Controller
//{
//    private function debugLog($message, $data = null)
//    {
//        $timestamp = date('Y-m-d H:i:s');
//        Log::channel('single')->info("[$timestamp] " . $message, $data ?? []);
//    }
//
//    private function assistantLog($message, $data = null)
//    {
//        $timestamp = date('Y-m-d H:i:s');
//        Log::channel('single')->info("[$timestamp] " . $message, $data ?? []);
//    }
//
//    public function chat(ChatRequest $request)
//    {
//        $this->debugLog('--- NEW CHAT REQUEST ---', $request->all());
//
//        $messages = array_values(array_filter(
//            $request->input('messages', []),
//            fn($m) => $m['role'] !== 'system'
//        ));
//
//        $user = auth('api')->user();
//        $userInfo = $user
//            ? "مشخصات کاربر وارد شده: نام: {$user->name}، شناسه (USER_LOGGED_IN_ID): {$user->id}"
//            : 'کاربر فعلی وارد نشده است.';
//
//        $systemPrompt = "
//تو دستیار هوشمند رزرو نوبت پزشکی پلتفرم 'آکاری' (Acaree) هستی.
//لحن: محترمانه، صمیمی و فقط به زبان فارسی.
//وظیفه تو **فقط و فقط** کمک به رزرو نوبت جدید است. تو اجازه لغو، ویرایش یا تغییر نوبت‌ها را نداری.
//
//قوانین حیاتی:
//۱. فقط دیتابیس: اطلاعات را حدس نزن. فقط از خروجی ابزارها استفاده کن.
//۲. شناسه USER_LOGGED_IN_ID مختص بیمار است. شناسه staff_id مختص پزشک است. هرگز این دو را جابجا نگیر.
//۳. نمایش نوبت‌ها: لیست ساعت‌های خالی را با تگ [UI:SELECT_TIME] نمایش بده.
//۴. در صورت خطای 'زمانبندی ثبت نشده'، به کاربر بگو برنامه کاری پزشک برای این روز پر است یا هنوز ثبت نشده است.
//
//جریان گفتگو:
//۱. جستجوی پزشک/تخصص (search_entities) -> نمایش با [UI:SELECT_STAFF]
//۲. دریافت جزئیات و خدمات پزشک (get_staff_details) -> نمایش با [UI:SELECT_SERVICE]
//۳. نمایش تقویم با [UI:SELECT_DATE]
//۴. دریافت نوبت‌های خالی (get_available_slots) -> نمایش با [UI:SELECT_TIME]
//۵. تایید نهایی: نمایش تگ [UI:CONFIRMATION] (منتظر تایید کاربر بمان و ابزاری صدا نزن).
//۶. ثبت نوبت: پس از تایید کاربر، ابزار book_appointment را صدا بزن.
//۷. برای پاسخ به سوالاتی مثل آدرس، شماره تلفن، بیمه‌ها، علائم بیماری یا تجهیزات کلینیک، حتماً از ابزار search_clinic_info استفاده کن و بر اساس خروجی آن به کاربر پاسخ محاوره‌ای بده. اطلاعات را از خودت حدس نزن.
//
//فرمت پاسخ‌های UI:
//- [UI:SELECT_STAFF:[{\"id\":1, \"name\":\"نام\", \"expertise\":\"تخصص\"}]]
//- [UI:SELECT_SERVICE:[{\"id\":1, \"name\":\"نام خدمت\", \"price\":1000}]]
//- [UI:SELECT_DATE:{\"staff_id\":1, \"service_id\":2}]
//- [UI:SELECT_TIME:{\"date\":\"2024-01-20\", \"staff_id\":1, \"service_id\":2, \"slots\":[{\"start_time\":\"08:00\", \"end_time\":\"08:30\"}]}]
//- [UI:CONFIRMATION:{\"staff_id\":1, \"service_id\":2, \"date\":\"2024-01-20\", \"time\":\"08:00\", \"staff_name\":\"نام پزشک\", \"service_name\":\"نام خدمت\"}]
//
//اطلاعات محیطی:
//- {$userInfo}
//- تاریخ امروز: " . Carbon::now()->format('Y-m-d') . " (امروز " . Carbon::now()->format('l') . " است)";
//
//        $tools = $this->tools();
//        $round = 0;
//        $maxRounds = 3;
//
//        while ($round < $maxRounds) {
//            $round++;
//            try {
//                $trimmedMessages = array_slice($messages, -8);
//                $result = $this->callLLM($trimmedMessages, $systemPrompt, $tools);
//
//                // بررسی وجود پیام در ساختار استاندارد
//                if (!isset($result['choices'][0]['message'])) {
//
//                    // بررسی اینکه آیا API خطایی برگردانده است یا خیر
//                    $errorDetails = 'پاسخ نامعتبر یا ساختار ناشناخته';
//                    if (isset($result['error'])) {
//                        $errorDetails = is_array($result['error']) ? json_encode($result['error'], JSON_UNESCAPED_UNICODE) : $result['error'];
//                    }
//
//                    Log::error('AI Invalid Response: ' . json_encode($result, JSON_UNESCAPED_UNICODE));
//
//                    return response()->json([
//                        'error' => [
//                            'message' => 'خطای API هوش مصنوعی: ' . $errorDetails,
//                            'raw_response' => $result // اضافه کردن این بخش موقتاً برای اینکه در فرانت‌اند هم ارور را ببینید
//                        ]
//                    ], 400);
//                }
//            } catch (\Exception $e) {
//                Log::error('AI Error: ' . $e->getMessage());
//                return response()->json(['error' => ['message' => 'خطای ارتباط با هوش مصنوعی: ' . $e->getMessage()]], 500);
//            }
//
//            $message = $result['choices'][0]['message'];
//
//            if (isset($message['content'])) {
//                $content = preg_replace('/<think>[\s\S]*?<\/think>/', '', $message['content']);
//                $content = preg_replace('/<think>[\s\S]*/', '', $content);
//                $message['content'] = trim($content);
//                $result['choices'][0]['message']['content'] = $message['content'];
//            }
//
//            if (empty($message['tool_calls'])) {
//                if (empty($message['content']) && $round === 1) {
//                    $result['choices'][0]['message']['content'] = 'چطور می‌توانم در رزرو نوبت به شما کمک کنم؟';
//                }
//                return $result;
//            }
//
//            $messages[] = $message;
//
//            foreach ($message['tool_calls'] as $toolCall) {
//                $toolName = $toolCall['function']['name'];
//                $toolArgs = json_decode($toolCall['function']['arguments'], true);
//                $output = $this->executeTool($toolName, $toolArgs);
//
//                $messages[] = [
//                    'role' => 'tool',
//                    'tool_call_id' => $toolCall['id'],
//                    'name' => $toolName,
//                    'content' => json_encode($output, JSON_UNESCAPED_UNICODE),
//                ];
//            }
//        }
//
//        return response()->json(['message' => 'زمان گفتگو بیش از حد طولانی شد.'], 500);
//    }
//
//    private function callLLM($messages, $systemPrompt, $tools)
//    {
//        return config('services.ai.provider') === 'arvan'
//            ? $this->callArvan($messages, $systemPrompt, $tools)
//            : $this->callOpenRouter($messages, $systemPrompt, $tools);
//    }
//
//
//    private function callOpenRouter($messages, $systemPrompt, $tools)
//    {
//        foreach (config('services.ai.openrouter.models') as $model) {
//            try {
//                $payload = [
//                    'model' => $model,
//                    'messages' => array_merge(
//                        [['role' => 'system', 'content' => $systemPrompt]],
//                        $messages
//                    ),
//                    'tools' => $tools,
//                    'tool_choice' => 'auto',
//                    'temperature' => 0.2,
//                    'max_tokens' => 600,
//                ];
//
//                $this->debugLog("Calling OpenRouter: Model={$model}", ['payload' => $payload]);
//
//                $response = Http::timeout(20)->withHeaders([
//                    'Authorization' => 'Bearer ' . config('services.ai.openrouter.key'),
//                ])->post(config('services.ai.openrouter.base_url'), $payload);
//
//                if ($response->successful()) {
//                    $this->debugLog("OpenRouter Success: Model={$model}");
//                    return $response->json();
//                }
//
//                $errorBody = $response->body();
//                $this->debugLog("OpenRouter Failed: Model={$model}, Status={$response->status()}, Response={$errorBody}");
//
//                Log::warning("OpenRouter Model {$model} failed: " . $errorBody);
//                continue;
//            } catch (\Throwable $e) {
//                $this->debugLog("OpenRouter Throwable: Model={$model}, Error={$e->getMessage()}");
//                Log::error('OpenRouter Error: ' . $e->getMessage());
//                continue;
//            }
//        }
//
//        throw new \Exception('تمامی مدل‌های هوش مصنوعی با خطا مواجه شدند.');
//    }
//
//    private function callArvan($messages, $systemPrompt, $tools)
//    {
//        $payload = [
//            'model' => config('services.ai.arvan.model'),
//            'messages' => array_merge(
//                [['role' => 'system', 'content' => $systemPrompt]],
//                $messages
//            ),
//            'tools' => $tools,
//            'tool_choice' => 'auto',
//            'temperature' => 0.2,
//            'max_tokens' => 600,
//        ];
//
//        $this->debugLog('Calling Arvan: Model=' . config('services.ai.arvan.model'), ['payload' => $payload]);
//
//        try {
//
//            $response = Http::timeout(15)
//                ->connectTimeout(20)
//                ->withHeaders([
//                    'Authorization' => 'Bearer ' . config('services.ai.arvan.key'),
//                    'Content-Type' => 'application/json',
//                ])
//                ->post(config('services.ai.arvan.base_url'), $payload);
//
//            if ($response->successful()) {
//                $this->debugLog('Arvan Success');
//                return $response->json();
//            }
//
//            $this->debugLog('Arvan Failed', [
//                'status' => $response->status(),
//                'body' => $response->body()
//            ]);
//            dd($response->status(), $response->body());
//
//
//            $errorData = $response->json();
//            $errorMessage = $errorData['error']['message']
//                ?? $errorData['message']
//                ?? 'خطای ناشناخته از سرویس هوش مصنوعی (Arvan)';
//
//            throw new \Exception($errorMessage);
//
//        } catch (\Throwable $e) {
//
//            \Log::error('Arvan Exception', [
//                'message' => $e->getMessage(),
//                'trace' => $e->getTraceAsString(),
//            ]);
//
//            throw $e;
//        }
//    }
//
//
//    /* ================= TOOLS ================= */
//
//    private function tools()
//    {
//        return [
//            [
//                'type' => 'function',
//                'function' => [
//                    'name' => 'search_entities',
//                    'description' => 'جستجوی پزشک، تخصص یا خدمت پزشکی به زبان فارسی.',
//                    'parameters' => [
//                        'type' => 'object',
//                        'properties' => [
//                            'query' => ['type' => 'string']
//                        ],
//                        'required' => ['query'],
//                    ],
//                ],
//            ],
//            [
//                'type' => 'function',
//                'function' => [
//                    'name' => 'get_staff_details',
//                    'description' => 'دریافت خدمات یک پزشک بر اساس شناسه (staff_id).',
//                    'parameters' => [
//                        'type' => 'object',
//                        'properties' => [
//                            'staff_id' => ['type' => 'integer'],
//                        ],
//                        'required' => ['staff_id'],
//                    ],
//                ],
//            ],
//            [
//                'type' => 'function',
//                'function' => [
//                    'name' => 'get_available_slots',
//                    'description' => 'دریافت زمان‌های خالی بر اساس شناسه پزشک، خدمت و تاریخ.',
//                    'parameters' => [
//                        'type' => 'object',
//                        'properties' => [
//                            'staff_id' => ['type' => 'integer'],
//                            'service_id' => ['type' => 'integer'],
//                            'date' => ['type' => 'string', 'description' => 'YYYY-MM-DD'],
//                        ],
//                        'required' => ['staff_id', 'service_id', 'date'],
//                    ],
//                ],
//            ],
//            [
//                'type' => 'function',
//                'function' => [
//                    'name' => 'book_appointment',
//                    'description' => 'ثبت نهایی رزرو پس از تایید کاربر.',
//                    'parameters' => [
//                        'type' => 'object',
//                        'properties' => [
//                            'staff_id' => ['type' => 'integer'],
//                            'service_id' => ['type' => 'integer'],
//                            'date_of_turn' => ['type' => 'string'],
//                            'start_time' => ['type' => 'string'],
//                        ],
//                        'required' => ['staff_id', 'service_id', 'date_of_turn', 'start_time'],
//                    ],
//                ],
//            ],
//            [
//                'type' => 'function',
//                'function' => [
//                    'name' => 'search_clinic_info',
//                    'description' => 'جستجوی اطلاعات کلینیک شامل: آدرس، شماره تماس، بیمه‌های طرف قرارداد، قوانین لغو نوبت، امکانات (مثل اکو فیلیپس) و بررسی علائم بیماری‌های قلبی.',
//                    'parameters' => [
//                        'type' => 'object',
//                        'properties' => [
//                            'query' => [
//                                'type' => 'string',
//                                'description' => 'سوال کاربر به صورت خلاصه برای جستجو در دیتابیس'
//                            ]
//                        ],
//                        'required' => ['query'],
//                    ],
//                ],
//            ],
//
//        ];
//    }
//
//    private function executeTool($name, $args)
//    {
//        try {
//            switch ($name) {
//                case 'search_entities':
//                    return $this->searchEntities($args);
//                case 'get_staff_details':
//                    return $this->getStaffDetails($args);
//                case 'get_available_slots':
//                    $result = app(AppointmentService::class)
//                        ->getAvailableSlots(new \App\Http\Requests\Appointment\AvailableSlotsRequest($args));
//                    return [
//                        'slots' => $result['data'] ?? [],
//                        'staff_id' => $args['staff_id'],
//                        'service_id' => $args['service_id'],
//                        'date' => $args['date']
//                    ];
//                case 'book_appointment':
//                    if (!auth('api')->check()) {
//                        return ['error' => 'ابتدا وارد حساب کاربری شوید.'];
//                    }
//                    return app(AppointmentService::class)
//                        ->addAppointment(new \App\Http\Requests\Appointment\AppointmentCreateRequest([
//                            'user_id' => auth('api')->id(),
//                            'staff_id' => $args['staff_id'],
//                            'service_id' => $args['service_id'],
//                            'date_of_turn' => $args['date_of_turn'],
//                            'start_time' => $args['start_time'],
//                            'type' => 'Online',
//                            'permissible_interference' => false,
//                            'resource_ids' => [] // اگر منبع خاصی نیاز است اضافه شود
//                        ]));
//                case 'search_clinic_info':
//                    return $this->searchClinicInfo($args);
//                default:
//                    return ['error' => 'ابزار یافت نشد'];
//            }
//        } catch (\Exception $e) {
//            Log::error("Tool Error ({$name}): " . $e->getMessage());
//            return ['error' => 'خطا در انجام عملیات.'];
//        }
//    }
//
//    private function searchEntities($args)
//    {
//        $q = trim($args['query']);
//        $searchTerms = ['دکتر', 'متخصص', 'آقای', 'خانم', 'پزشک', 'دکترای', 'جراح', 'کلینیک', 'بیمارستان', 'نوبت'];
//        $cleanQ = trim(str_replace($searchTerms, '', $q));
//        $words = array_filter(explode(' ', $cleanQ), fn($w) => mb_strlen($w) > 1);
//
//        $expertises = cache()->remember('expertises_list', 3600, function () {
//            return Expertise::all(['id', 'title', 'label']);
//        });
//
//        $englishExpertise = null;
//        $queryWords = preg_split('/\s+/u', $cleanQ);
//
//        foreach ($expertises as $exp) {
//            $label = str_replace('‌', '', $exp->label);
//            if ($cleanQ === $label || count(array_intersect($queryWords, preg_split('/\s+/u', $label))) > 0) {
//                $englishExpertise = $exp->title;
//                break;
//            }
//        }
//
//        $staffQuery = Staff::query()
//            ->select(['id', 'user_id', 'expertise_id'])
//            ->with(['user:id,name', 'expertise:id,title,label']);
//
//        if ($englishExpertise) {
//            $staffQuery->whereHas('expertise', fn($query) => $query->where('title', 'like', "%$englishExpertise%"));
//        } elseif (!empty($words)) {
//            $staffQuery->where(function ($query) use ($words) {
//                foreach ($words as $word) {
//                    $query->orWhereHas('user', fn($q) => $q->where('name', 'like', "%$word%"))
//                          ->orWhereHas('expertise', fn($q) => $q->where('title', 'like', "%$word%")->orWhere('label', 'like', "%$word%"));
//                }
//            });
//        } else {
//            $staffQuery->limit(10); // خروجی پیش‌فرض در صورت خالی بودن
//        }
//
//        $staff = $staffQuery->take(10)->get()->map(fn($s) => [
//            'type' => 'staff',
//            'id' => $s->id,
//            'name' => $s->user->name ?? 'بدون نام',
//            'expertise' => $s->expertise ? ($s->expertise->label ?: $s->expertise->title) : 'پزشک عمومی',
//        ]);
//
//        return ['results' => $staff->toArray()];
//    }
//
//    private function getStaffDetails($args)
//    {
//        $staff = Staff::with(['user:id,name', 'expertise:id,title,label'])->find($args['staff_id']);
//        if (!$staff) return ['error' => 'پزشک پیدا نشد'];
//
//        // استفاده مستقیم از دیتابیس برای افزایش سرعت به جای استفاده از مپینگ سنگین
//        $services = Service::query()
//            ->select('services.id', 'services.title', 'services.price')
//            ->join('appointments', 'appointments.service_id', '=', 'services.id')
//            ->where('appointments.staff_id', $staff->id)
//            ->distinct()
//            ->get();
//
//        return [
//            'id' => $staff->id,
//            'name' => $staff->user->name ?? 'بدون نام',
//            'expertise' => $staff->expertise ? ($staff->expertise->label ?: $staff->expertise->title) : 'پزشک عمومی',
//            'services' => $services->toArray(),
//        ];
//    }
//
//    private function searchClinicInfo($args)
//    {
//        $query = $args['query'] ?? '';
//
//        try {
//            // ارسال درخواست به میکروسرویس پایتون که قبلا نوشتید
//            $response = Http::timeout(10)->post('http://127.0.0.1:8000/search-faiss', [
//                'sentence' => $query
//            ]);
//
//            if ($response->successful()) {
//                $data = $response->json();
//
//                // استخراج فقط متن جملات برای ارسال به LLM تا توکن کمتری مصرف شود
//                $sentences = [];
//                if (!empty($data['results'])) {
//                    foreach ($data['results'] as $result) {
//                        $sentences[] = $result['sentence'];
//                    }
//                }
//
//                if (empty($sentences)) {
//                    return ['message' => 'اطلاعاتی در این باره یافت نشد. به کاربر بگو با پذیرش تماس بگیرد.'];
//                }
//
//                return [
//                    'retrieved_information' => $sentences,
//                    'instruction' => 'با استفاده از اطلاعات بالا، یک پاسخ طبیعی، محترمانه و کوتاه به کاربر بده.'
//                ];
//            }
//
//            return ['error' => 'ارتباط با سرویس جستجوی اطلاعات قطع است.'];
//
//        } catch (\Exception $e) {
//            Log::error('Qdrant Search Error: ' . $e->getMessage());
//            return ['error' => 'خطا در جستجوی اطلاعات کلینیک.'];
//        }
//    }
//
//
//
//}
