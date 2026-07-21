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

    /**
 * @OA\Post(
 *     path="/ai/chat",
 *     tags={"AI Chat"},
 *     summary="ارسال پیام به دستیار هوشمند رزرو نوبت",
 *     description="این endpoint یک دستیار هوشمند مبتنی بر LLM است که دو قابلیت اصلی دارد:
 *
 * **۱. رزرو نوبت (Appointment Flow):**
 * کاربر می‌تواند به صورت مکالمه‌ای اطلاعات رزرو را تکمیل کند. سیستم به صورت خودکار
 * نام پزشک، خدمت، تاریخ و ساعت را از پیام کاربر استخراج می‌کند (Slot Filling).
 * پس از تکمیل تمام فیلدها، نوبت به صورت خودکار ثبت می‌شود.
 *
 * **۲. پشتیبانی و سوالات عمومی (Support Flow):**
 * سوالات عمومی درباره کلینیک از طریق جستجوی RAG در اسناد کلینیک پاسخ داده می‌شود.
 *
 * **نحوه مکالمه چندمرحله‌ای:**
 * در هر درخواست، آرایه messages را با تمام تاریخچه مکالمه بفرستید.
 * مقدار current_slots بازگشتی از پاسخ قبلی را نیز در درخواست بعدی include کنید
 * تا حافظه مکالمه حفظ شود.
 *
 * **⚠️ نکته ۱ — current_slots در response:**
 * فقط در جریان رزرو برگشت داده می‌شود. در جریان پشتیبانی این فیلد در response وجود ندارد؛
 * کلاینت باید null-check انجام دهد.
 *
 * **⚠️ نکته ۲ — مکالمه چندمرحله‌ای:**
 * کلاینت باید هر بار هم messages کامل و هم current_slots از پاسخ قبلی را بفرستد.
 * در صورت فراموش کردن current_slots، هر پیام مثل یک مکالمه جدید پردازش می‌شود.
 *
 * **⚠️ نکته ۳ — ثبت موفق نوبت:**
 * وقتی همه ۴ اسلات (پزشک، خدمت، تاریخ، ساعت) تکمیل شوند و نوبت ثبت شود،
 * فیلد current_slots دیگر در response ارسال نمی‌شود و فقط choices با پیام تأیید برمی‌گردد.
 * کلاینت باید این حالت را تشخیص داده و state محلی رزرو را ریست کند.",
 *     security={{"bearerAuth":{}}},
 *     @OA\RequestBody(
 *         required=true,
 *         @OA\JsonContent(
 *             required={"messages"},
 *             @OA\Property(
 *                 property="messages",
 *                 type="array",
 *                 description="تاریخچه کامل مکالمه. پیام‌های system به صورت خودکار فیلتر می‌شوند.",
 *                 @OA\Items(
 *                     type="object",
 *                     required={"role","content"},
 *                     @OA\Property(
 *                         property="role",
 *                         type="string",
 *                         enum={"user","assistant"},
 *                         description="نقش فرستنده پیام",
 *                         example="user"
 *                     ),
 *                     @OA\Property(
 *                         property="content",
 *                         type="string",
 *                         description="متن پیام",
 *                         example="می‌خوام با دکتر احمدی نوبت بگیرم"
 *                     )
 *                 ),
 *                 example={
 *                     {"role":"user","content":"سلام"},
 *                     {"role":"assistant","content":"سلام! چطور می‌تونم کمکتون کنم؟"},
 *                     {"role":"user","content":"می‌خوام با دکتر احمدی نوبت بگیرم"}
 *                 }
 *             ),
 *             @OA\Property(
 *                 property="current_slots",
 *                 type="object",
 *                 nullable=true,
 *                 description="وضعیت فعلی اسلات‌های رزرو. مقدار بازگشتی از پاسخ قبلی را اینجا بفرستید تا حافظه مکالمه حفظ شود. اگر ارسال نشود هر پیام به عنوان مکالمه جدید پردازش می‌شود.",
 *                 @OA\Property(property="doctor_name", type="string", nullable=true, description="نام پزشک استخراج‌شده از مکالمه قبلی", example="دکتر علی احمدی"),
 *                 @OA\Property(property="service_name", type="string", nullable=true, description="نام خدمت استخراج‌شده از مکالمه قبلی", example="اکوکاردیوگرافی"),
 *                 @OA\Property(property="date", type="string", nullable=true, description="تاریخ رزرو به فرمت Y-m-d یا عبارت نسبی مثل فردا", example="2026-06-10"),
 *                 @OA\Property(property="start_time", type="string", nullable=true, description="ساعت شروع به فرمت HH:mm", example="09:30")
 *             )
 *         )
 *     ),
 *     @OA\Response(
 *         response=200,
 *         description="پاسخ موفق دستیار هوشمند",
 *         @OA\JsonContent(
 *             @OA\Property(
 *                 property="choices",
 *                 type="array",
 *                 description="آرایه پاسخ‌های مدل، سازگار با فرمت OpenAI. همیشه در response وجود دارد.",
 *                 @OA\Items(
 *                     type="object",
 *                     @OA\Property(
 *                         property="message",
 *                         type="object",
 *                         @OA\Property(property="role", type="string", example="assistant"),
 *                         @OA\Property(
 *                             property="content",
 *                             type="string",
 *                             description="پاسخ متنی دستیار به فارسی",
 *                             example="پزشکان موجود ما: دکتر علی احمدی، دکتر مریم رضایی. کدام را انتخاب می‌کنید؟"
 *                         )
 *                     )
 *                 )
 *             ),
 *             @OA\Property(
 *                 property="current_slots",
 *                 type="object",
 *                 nullable=true,
 *                 description="وضعیت به‌روز شده اسلات‌های رزرو. این مقدار را در درخواست بعدی به عنوان current_slots بفرستید. ⚠️ فقط در جریان رزرو برگردانده می‌شود — در جریان پشتیبانی و پس از ثبت موفق نوبت این فیلد در response وجود ندارد. کلاینت باید null-check انجام دهد و در صورت نبود این فیلد، state محلی رزرو را ریست کند.",
 *                 @OA\Property(property="doctor_name", type="string", nullable=true, example="دکتر علی احمدی"),
 *                 @OA\Property(property="service_name", type="string", nullable=true, example="اکوکاردیوگرافی"),
 *                 @OA\Property(property="date", type="string", nullable=true, example="2026-06-10"),
 *                 @OA\Property(property="start_time", type="string", nullable=true, example="09:30"),
 *                 @OA\Property(property="user_id", type="integer", nullable=true, description="شناسه کاربر احراز هویت‌شده", example=42)
 *             )
 *         )
 *     ),
 *     @OA\Response(
 *         response=400,
 *         description="پیام کاربر خالی است",
 *         @OA\JsonContent(
 *             @OA\Property(property="message", type="string", example="پیام نمی‌تواند خالی باشد.")
 *         )
 *     ),
 *     @OA\Response(
 *         response=401,
 *         description="توکن احراز هویت ارسال نشده یا منقضی شده است",
 *         @OA\JsonContent(
 *             @OA\Property(property="message", type="string", example="Unauthenticated.")
 *         )
 *     ),
 *     @OA\Response(
 *         response=422,
 *         description="خطای اعتبارسنجی داده‌های ورودی",
 *         @OA\JsonContent(
 *             @OA\Property(property="message", type="string", example="The messages field is required."),
 *             @OA\Property(
 *                 property="errors",
 *                 type="object",
 *                 example={"messages":{"The messages field is required."}}
 *             )
 *         )
 *     ),
 *     @OA\Response(
 *         response=500,
 *         description="خطای داخلی سرور یا عدم دسترسی به سرویس هوش مصنوعی",
 *         @OA\JsonContent(
 *             @OA\Property(
 *                 property="error",
 *                 type="object",
 *                 @OA\Property(property="message", type="string", example="خطا در پردازش درخواست شما.")
 *             )
 *         )
 *     )
 * )
 */
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

    $this->logAi(str_repeat('─', 50));
    $this->logAi('کاربر: ' . $this->stripAiSyntax($lastUserMessage));

    try {

        // بررسی اینکه آیا کاربر در حال طی کردن مراحل رزرو است؟
        // اگر نام دکتر یا خدمت از قبل مشخص شده، یعنی کاربر در "جریان رزرو" قرار دارد.
        $isInBookingProcess = !empty($previousState['doctor_name']) || !empty($previousState['service_name']);

        if ($isInBookingProcess) {
            // بدون توجه به خروجی Router، به نوبت‌دهی ادامه بده
            return $this->handleAppointmentIntent($messages, $lastUserMessage, $previousState);
        }

        // اگر کاربر تازه مکالمه را شروع کرده یا هیچ اسلاتی پر نشده، حالا مسیریابی کن
        $routeResponse = Http::timeout(20)->post("{$this->pythonServiceUrl}/route", [  // فیز
            'sentence' => $lastUserMessage
        ]);

        //فیز چه تشخیصی داده
        $routeData = $routeResponse->json();
        $intent = $routeData['intent'] ?? 'appointment';
        $score = $routeData['score'] ?? 0;
        $reason = $routeData['reason'] ?? '';

        $this->logAi("FAISS: intent={$intent}  score=" . round((float) $score, 2) . "  reason={$reason}");

        // سرویس FAISS خودش تصمیم نهایی intent را می‌گیرد (شامل تشخیص کلمات کلیدی صریح مثل 'آدرس'/'تلفن').
        // score همیشه امتیاز جستجوی برداری است، نه میزان اطمینان از این تصمیم؛ پس نباید دوباره روی آن آستانه بگذاریم.
        if ($intent === 'support') {
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
            foreach ($qdrantResponse->json()['results'] as $row) {               //خروجی فیز ممکنه چندین جمله باشه که به جمله کاربر مرتبطه
                $retrievedTexts[] = $row['sentence'];              // همرو میریزه تو یه ارایه
            }
        }

        if (empty($retrievedTexts)) {   //اگه فیز هیچ جمله ای پیدا نکنه:
            return response()->json([
                'choices' => [[
                    'message' => [
                        'role' => 'assistant',
                        'content' => 'متاسفانه اطلاعاتی در این زمینه پیدا نکردم. لطفاً با شماره تلفن ۳۳۳۳۳۳۳۶ تماس بگیرید.'
                    ]
                ]]
            ]);
        }
        //حالا جملات فیزو میه به مدل تا یه خروجی ترکیبی و نهایی بگیره و بده کاربر

        // ۲. ساخت پرامپت به شدت مینی‌مال فقط برای پاسخ متنی
        $systemPrompt = 'تو بخش پشتیبانی و روابط عمومی کلینیک پزشکی آکاری هستی.
با استفاده از اطلاعات مستند زیر، به سوال کاربر پاسخ کوتاه، محترمانه و صمیمی به زبان فارسی بده.
حق نداری اطلاعاتی خارج از متن زیر ارائه کنی یا حدس بزنی.

مستندات کلینیک:
' . implode("\n", $retrievedTexts);

        // ارسال به مدل بدون تعریف هیچ نوع ابزاری (کاهش شدید حجم توکن)
        return $this->callLLMRaw($messages, $systemPrompt, 'پشتیبانی');
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
        $aiResponse = $this->callLLMRaw([['role' => 'user', 'content' => $lastUserMessage]], $systemPrompt, 'استخراج اطلاعات رزرو');
        $aiContent = preg_replace('/<think>[\s\S]*?<\/think>/', '', $aiResponse['choices'][0]['message']['content'] ?? ''); //حذف تگهای اضافی خروجی مدل

        if (preg_match('/\{[\s\S]*\}/', $aiContent, $matches)) {  //جیسون رو از داخل متن پیدا میکنه
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
        $doctorOptions = []; // برای نمایش لیست انتخاب پزشک در فرانت (UI tag)
        if (!empty($slots['doctor_name'])) {
            $cleanName = trim(str_replace(['دکتر', 'متخصص'], '', $slots['doctor_name']));

            // پیدا کردن استفی که کاربرش نام مشابه دارد و نقش آن دکتر است
            $staffFound = Staff::whereHas('user', function ($q) use ($cleanName) {
                $q->where('role', UserRole::doctor->value)->where('name', 'like', "%{$cleanName}%");
            })->first();

            if ($staffFound) {
                $slots['doctor_name'] = $staffFound->user->name;
            } else {
                // اگر اسم اشتباه بود، لیست تمام پزشکان را می‌گیریم
                $doctorOptions = $this->getDoctorOptions();

                $staffHelperText = "پزشکی با نام '{$slots['doctor_name']}' پیدا نشد. لیست پزشکان معتبر ما: [" . collect($doctorOptions)->pluck('name')->implode('، ') . ']';
                $slots['doctor_name'] = null;
            }
        } else {
            // اگر کاربر هنوز نام پزشک را نگفته، لیست دکترا را از دیتابیس بکش
            $doctorOptions = $this->getDoctorOptions();
            if (!empty($doctorOptions)) {
                $staffHelperText = 'کاربر هنوز نام پزشک را نگفته است. حتماً لیست این پزشکان را به او نشان بده تا یکی را انتخاب کند: [' . collect($doctorOptions)->pluck('name')->implode('، ') . ']';
            }
        }

        // ۲. شناسایی خدمت
        $serviceFound = null;
        $serviceOptions = []; // برای نمایش لیست انتخاب خدمت در فرانت (UI tag)
        if (!empty($slots['service_name'])) {
            // پاکسازی نام خدمت برای جستجوی بهتر
            $searchTerm = trim($slots['service_name']);

            $serviceFound = \App\Models\Service::where('title', 'like', "%{$searchTerm}%")->first();

            if ($serviceFound) {
                $slots['service_name'] = $serviceFound->title;
                // نکته مهم: اینجا باید مقدار helper رو خالی کنی که هوش مصنوعی گیج نشه
                $serviceHelperText = "خدمت انتخاب شده: {$serviceFound->title}";
            } else {
                $serviceOptions = $this->getServiceOptions();
                $serviceHelperText = 'کاربر خدمتی گفت که در لیست نیست. لیست دقیق خدمات ما: [' . collect($serviceOptions)->pluck('name')->implode('، ') . ']. از کاربر بخواه دقیقاً یکی از این موارد را انتخاب کند.';
                $slots['service_name'] = null; // ریست کن تا دوباره بپرسه
            }
        } else {
            $serviceOptions = $this->getServiceOptions();
            if (!empty($serviceOptions)) {
                $serviceHelperText = 'کاربر هنوز خدمتی انتخاب نکرده است. حتماً این لیست دقیق را به کاربر نشان بده تا انتخاب کند: [' . collect($serviceOptions)->pluck('name')->implode('، ') . ']';
            }
        }


        // ۳. بررسی تاریخ و استخراج زمان‌های خالی
        $timeSlotOptions = []; // برای نمایش لیست زمان‌های خالی در فرانت (UI tag)
        if ($staffFound && $serviceFound) {
            if (empty($slots['date'])) {
                // اگر تاریخ نداریم، از کاربر بخواهیم تاریخ بدهد
                $slotsText = "هنوز تاریخی انتخاب نشده است. از کاربر بخواه برای چه روزی (مثلاً فردا، شنبه یا ...) نوبت می‌خواهد.";
            } else {
                $standardDate = $this->convertRelativeDateToStandard($slots['date']);
                // نگه‌داشتن تاریخ استاندارد به‌جای عبارت نسبی خام (مثل '2 شنبه') تا در پاسخ به کاربر و مراحل بعدی هم درست نمایش داده شود
                $slots['date'] = $standardDate;

                $availableSlotsRequest = new \App\Http\Requests\Appointment\AvailableSlotsRequest([
                    'staff_id' => $staffFound->id,
                    'service_id' => $serviceFound->id,
                    'date' => $standardDate
                ]);

                try {
                    $availableData = $this->appointmentService->getAvailableSlots($availableSlotsRequest);
                    $availableSlots = $availableData['data'] ?? [];

                    if (empty($availableSlots)) {
                        $slotsText = "متاسفانه برای تاریخ {$standardDate} هیچ زمان خالی پیدا نشد. از کاربر بخواه روز دیگری را انتخاب کند.";
                        $slots['date'] = null; // ریست کردن تاریخ برای پرسش مجدد
                    } else {
                        $times = collect($availableSlots)->map(fn($s) => $s['start_time'])->take(8)->implode('، ');
                        // مقدار واقعی که باید به هوش مصنوعی برسد
                        $slotsText = "زمان‌های خالی در تاریخ {$standardDate}: [{$times}]. حتماً این زمان‌ها را به کاربر نشان بده تا یکی را انتخاب کند.";
                        $timeSlotOptions = collect($availableSlots)->map(fn($s) => ['start_time' => $s['start_time']])->values()->all();
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

                return $this->callLLMRaw($messages, $finalPrompt, 'تایید نوبت');

            } catch (\Exception $e) {
                Log::error('Appointment Booking Error: ' . $e->getMessage());
                $errorPrompt = 'متاسفانه مشکلی در ثبت نهایی پیش اومد: ' . $e->getMessage() . '. محترمانه عذرخواهی کن.';
                return $this->callLLMRaw($messages, $errorPrompt, 'خطای ثبت نوبت');
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

        $aiFinalResponse = $this->callLLMRaw($messages, $finalPrompt, 'وضعیت رزرو');

        // ۶. تعیین اینکه کدام کامپوننت UI (اگر لازم بود) به فرانت نشان داده شود
        // اولویت: انتخاب پزشک > انتخاب خدمت > تقویم تاریخ > لیست ساعت‌های خالی
        if (!$staffFound && !empty($doctorOptions)) {
            $aiFinalResponse = $this->appendUiTag($aiFinalResponse, 'SELECT_STAFF', $doctorOptions);
        } elseif (!$serviceFound && !empty($serviceOptions)) {
            $aiFinalResponse = $this->appendUiTag($aiFinalResponse, 'SELECT_SERVICE', $serviceOptions);
        } elseif ($staffFound && $serviceFound && empty($slots['date'])) {
            $aiFinalResponse = $this->appendUiTag($aiFinalResponse, 'SELECT_DATE', [
                'staff_id' => $staffFound->id,
                'service_id' => $serviceFound->id,
            ]);
        } elseif (!empty($timeSlotOptions)) {
            $aiFinalResponse = $this->appendUiTag($aiFinalResponse, 'SELECT_TIME', [
                'date' => $slots['date'],
                'staff_id' => $staffFound->id,
                'service_id' => $serviceFound->id,
                'slots' => $timeSlotOptions,
            ]);
        }

        return response()->json([
            'choices' => $aiFinalResponse['choices'],
            'current_slots' => $slots // فرستادن حافظه آپدیت شده به کاربر
        ]);
    }

    /**
     * لیست پزشکان برای نمایش در UI انتخاب پزشک (id, name, expertise)
     */
    private function getDoctorOptions(): array
    {
        return Staff::with(['user', 'expertise'])
            ->whereHas('user', fn ($q) => $q->where('role', UserRole::doctor->value))
            ->get()
            ->map(fn (Staff $staff) => [
                'id' => $staff->id,
                'name' => $staff->user->name,
                'expertise' => $staff->expertise?->title,
            ])
            ->values()
            ->all();
    }

    /**
     * لیست خدمات برای نمایش در UI انتخاب خدمت (id, name, price)
     */
    private function getServiceOptions(): array
    {
        return Service::all()
            ->map(fn (Service $service) => [
                'id' => $service->id,
                'name' => $service->title,
                'price' => $service->price,
            ])
            ->values()
            ->all();
    }

    /**
     * افزودن تگ ساختاریافته [UI:TYPE:{json}] به انتهای پاسخ متنی مدل،
     * تا فرانت بتواند کامپوننت مناسب (تقویم، لیست انتخاب، ...) را نمایش دهد.
     * این تگ مستقیماً توسط بک‌اند ساخته می‌شود، نه مدل زبانی — پس همیشه JSON معتبر است.
     */
    private function appendUiTag(array $llmResult, string $uiType, array $data): array
    {
        $content = $llmResult['choices'][0]['message']['content'] ?? '';
        // مدل زبانی گاهی خودش یک تگ [UI:...] ناقص/جعلی در متن می‌نویسد؛ قبل از افزودن تگ واقعی حذفش می‌کنیم
        // تا فرانت با دو تگ (یکی نامعتبر، یکی معتبر) مواجه نشود.
        $content = preg_replace('/\[UI:[A-Z_]+:[\s\S]*/', '', $content) ?? $content;

        $tag = "[UI:{$uiType}:" . json_encode($data, JSON_UNESCAPED_UNICODE) . ']';
        $llmResult['choices'][0]['message']['content'] = trim($content) . "\n" . $tag;

        return $llmResult;
    }

    /**
     * تابع کمکی برای تبدیل "فردا"، "پس‌فردا" یا روزهای هفته به تاریخ استاندارد
     */
    private function convertRelativeDateToStandard($relativeDate)
    {
        // یک تاریخ Y-m-d معتبر که از قبل تبدیل شده را دست‌نخورده برگردان
        if (preg_match('/^\d{4}-\d{2}-\d{2}$/', trim($relativeDate ?? ''))) {
            return trim($relativeDate);
        }

        // نرمال‌سازی: حذف فاصله‌ها و تبدیل ارقام فارسی/عربی به لاتین تا 'دو شنبه'، '۲ شنبه' و 'دوشنبه' یکسان مچ شوند
        $normalized = str_replace(' ', '', $relativeDate ?? '');
        $normalized = strtr($normalized, [
            '۰' => '0', '۱' => '1', '۲' => '2', '۳' => '3', '۴' => '4',
            '۵' => '5', '۶' => '6', '۷' => '7', '۸' => '8', '۹' => '9',
            '٠' => '0', '١' => '1', '٢' => '2', '٣' => '3', '٤' => '4',
            '٥' => '5', '٦' => '6', '٧' => '7', '٨' => '8', '٩' => '9',
        ]);

        $date = now();

        if (str_contains($normalized, 'پسفردا')) {
            $date->addDays(2);
            return $date->format('Y-m-d');
        }

        if (str_contains($normalized, 'فردا')) {
            $date->addDay();
            return $date->format('Y-m-d');
        }

        // نگاشت روزهای هفته؛ همچنین شکل عامیانه عددی (۱شنبه=شنبه ... ۶شنبه=پنج‌شنبه) پشتیبانی می‌شود.
        // نکته: کلیدهای اختصاصی‌تر باید قبل از 'شنبه' خام چک شوند چون همه‌ی روزها شامل زیررشته‌ی 'شنبه' هستند.
        $days = [
            '1شنبه' => Carbon::SATURDAY,
            'یکشنبه' => Carbon::SUNDAY, '2شنبه' => Carbon::SUNDAY,
            'دوشنبه' => Carbon::MONDAY, '3شنبه' => Carbon::MONDAY,
            'سه‌شنبه' => Carbon::TUESDAY, 'سهشنبه' => Carbon::TUESDAY, '4شنبه' => Carbon::TUESDAY,
            'چهارشنبه' => Carbon::WEDNESDAY, '5شنبه' => Carbon::WEDNESDAY,
            'پنج‌شنبه' => Carbon::THURSDAY, 'پنجشنبه' => Carbon::THURSDAY, '6شنبه' => Carbon::THURSDAY,
            'جمعه' => Carbon::FRIDAY,
            'شنبه' => Carbon::SATURDAY,
        ];

        foreach ($days as $dayName => $dayConstant) {
            if (str_contains($normalized, $dayName)) {
                $date->next($dayConstant);
                return $date->format('Y-m-d');
            }
        }

        return $date->format('Y-m-d');
    }    /**
     * متد عمومی و سبک برای ارتباط با مدل‌های زبانی (بدون ساختار پیچیده Tools)
     */
    private function callLLMRaw($messages, $systemPrompt, string $label = 'پاسخ')
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
            'temperature' => 0.2,   //خلاقیت کم و پاسخ ها منطقی
            'max_tokens' => 400, // کاهش تعداد توکن خروجی برای بهینه‌سازی سرعت
        ];

        $lastMessageForLog = collect($messages)->last()['content'] ?? '';
        $this->logAi("→ اروان ({$label}): " . $this->stripAiSyntax($lastMessageForLog));

        $response = Http::timeout(20)->connectTimeout(10)->withHeaders([
            'Authorization' => 'Bearer ' . $apiKey,
            'Content-Type' => 'application/json',
        ])->post($baseUrl, $payload);

        if ($response->successful()) {
            $result = $response->json();
            $reply = $result['choices'][0]['message']['content'] ?? '';
            $this->logAi('← اروان: ' . $this->stripAiSyntax($reply));

            return $result;
        }

        $this->logAi("✗ خطای اروان ({$label}): HTTP {$response->status()}");

        throw new \Exception('خطا در برقراری ارتباط با LLM: ' . $response->body());
    }

    /**
     * نوشتن یک خط در لاگ تمیز مکالمات AI (storage/logs/ai-chat.log)
     */
    private function logAi(string $line): void
    {
        Log::channel('ai_chat')->info($line);
    }


    private function stripAiSyntax(string $text): string                  //خروجی مدلو میگیرهو یسری تگارو حذف میکنه تا فقط متن معمولی بمونه
    {
        $text = preg_replace('/<think>[\s\S]*?<\/think>/', '', $text) ?? $text;
        $text = preg_replace('/\[UI:[A-Z_]+:[\s\S]*\]/', '', $text) ?? $text;
        $text = preg_replace('/\[BTN:.*?:.*?\]/', '', $text) ?? $text;
        $text = trim(preg_replace('/\n{2,}/', ' ', $text) ?? $text);

        return $text;
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
