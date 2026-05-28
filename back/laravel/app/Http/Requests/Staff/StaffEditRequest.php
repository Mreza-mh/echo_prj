<?php

namespace App\Http\Requests\Staff;

use App\Enums\StaffRoleType;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Validation\Rule;

class StaffEditRequest extends FormRequest
{
    protected $stopOnFirstFailure = true;
    public function authorize()
    {
        return true;
    }
    protected function failedValidation(Validator $validator)
    {
        $errorMessage = $validator->errors()->first();
        throw new HttpResponseException(response()->json(['message' => $errorMessage,'success' => false], 400));
    }
    public function rules(): array
    {
        return [
            'user_id'         => ['nullable', 'integer', 'exists:users,id'],
            'expertise_id'    => ['nullable', 'integer', 'exists:expertises,id'],
            'schedule' => ['nullable', 'array', 'min:1'],
            'schedule.*.day'        => ['nullable', 'in:sat,sun,mon,tue,wed,thu,fri'],
            'schedule.*.start_time' => ['nullable', 'date_format:H:i:s'],
            'schedule.*.end_time'   => ['nullable', 'date_format:H:i:s', 'after:schedule.*.start_time'],
        ];
    }

    public function messages(): array
    {
        return [
            'user_id.integer'          => 'شناسه کاربر باید عدد باشد.',
            'user_id.exists'           => 'کاربر انتخاب‌شده معتبر نیست.',

            'expertise_id.integer'     => 'شناسه تخصص باید عدد باشد.',
            'expertise_id.exists'      => 'تخصص انتخاب‌شده معتبر نیست.',

            'schedule.array'    => 'برنامه باید به صورت آرایه باشد.',
            'schedule.min'      => 'برنامه باید حداقل یک روز داشته باشد.',

            'schedule.*.day.in'              => 'روز وارد شده معتبر نیست.',
            'schedule.*.start_time.required' => 'زمان شروع الزامی است.',
            'schedule.*.start_time.date_format' => 'زمان شروع باید به فرمت HH:MM:SS باشد.',
            'schedule.*.end_time.required'   => 'زمان پایان الزامی است.',
            'schedule.*.end_time.date_format' => 'زمان پایان باید به فرمت HH:MM:SS باشد.',
            'schedule.*.end_time.after'      => 'زمان پایان باید بعد از زمان شروع باشد.',
        ];
    }
}
