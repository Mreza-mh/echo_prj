<?php

namespace App\Http\Requests\Ai;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;

class ChatRequest extends FormRequest
{
    /**
     * تعیین اینکه آیا کاربر اجازه ارسال این درخواست را دارد یا خیر.
     */
    public function authorize(): bool
    {
        // با توجه به اینکه در کنترلر از auth('api') استفاده کرده‌اید،
        // اینجا می‌توانید true بگذارید یا شرط ورود را چک کنید.
        return true;
    }

    /**
     * قوانین اعتبارسنجی
     */
    public function rules(): array
    {
        return [
            'messages' => 'required|array|min:1',
            'messages.*.role' => 'required|string|in:user,assistant,system,tool',
            'messages.*.content' => 'present|nullable|string',
            // اگر فیلدهای مربوط به Tool Callها هم از سمت کلاینت ارسال می‌شوند:
            'messages.*.tool_call_id' => 'nullable|string',
            'messages.*.name' => 'nullable|string',
        ];
    }

    /**
     * سفارشی‌سازی نام فیلدها برای پیام خطا
     */
    public function attributes(): array
    {
        return [
            'messages' => 'تاریخچه گفتگو',
            'messages.*.role' => 'نقش فرستنده',
            'messages.*.content' => 'محتوای پیام',
        ];
    }

    /**
     * پیام‌های خطای فارسی
     */
    public function messages(): array
    {
        return [
            'messages.required' => 'ارسال تاریخچه پیام‌ها الزامی است.',
            'messages.array' => 'ساختار پیام‌ها باید به صورت آرایه باشد.',
            'messages.*.role.required' => 'نقش فرستنده پیام مشخص نشده است.',
            'messages.*.role.in' => 'نقش ارسال کننده باید یکی از موارد user، assistant یا tool باشد.',
            'messages.*.content.present' => 'فیلد محتوا باید در درخواست وجود داشته باشد.',
        ];
    }

    /**
     * نحوه برخورد با خطای اعتبارسنجی (ارسال پاسخ JSON)
     */
    protected function failedValidation(Validator $validator)
    {
        throw new HttpResponseException(response()->json([
            'error' => [
                'message' => 'اطلاعات ارسالی معتبر نیست.',
                'details' => $validator->errors()
            ]
        ], 422));
    }
}
