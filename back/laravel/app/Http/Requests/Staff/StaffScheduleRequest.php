<?php

namespace App\Http\Requests\Staff;

use App\Enums\StaffRoleType;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Validation\Rule;

class StaffScheduleRequest extends FormRequest
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
            'schedule' => ['required', 'array', 'min:1'],
            'schedule.*.day'        => ['required', 'in:sat,sun,mon,tue,wed,thu,fri'],
            'schedule.*.start_time' => ['required', 'date_format:H:i:s'],
            'schedule.*.end_time'   => ['required', 'date_format:H:i:s', 'after:schedule.*.start_time'],

        ];
    }

    public function messages(): array
    {
        return [
            'schedule.required' => 'برنامه زمانی الزامی است.',
            'schedule.array'    => 'برنامه باید به صورت آرایه باشد.',
            'schedule.min'      => 'برنامه باید حداقل یک روز داشته باشد.',
            'schedule.*.day.required'        => 'روز الزامی است.',
            'schedule.*.day.in'              => 'روز وارد شده معتبر نیست.',
            'schedule.*.start_time.required' => 'زمان شروع الزامی است.',
            'schedule.*.start_time.date_format' => 'زمان شروع باید به فرمت HH:MM:SS باشد.',
            'schedule.*.end_time.required'   => 'زمان پایان الزامی است.',
            'schedule.*.end_time.date_format' => 'زمان پایان باید به فرمت HH:MM:SS باشد.',
            'schedule.*.end_time.after'      => 'زمان پایان باید بعد از زمان شروع باشد.',




        ];
    }
}
