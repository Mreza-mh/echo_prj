<?php

namespace App\Http\Requests\Appointment;

use Illuminate\Foundation\Http\FormRequest;

class AvailableSlotsRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'service_id' => ['required', 'integer', 'exists:services,id'],
            'staff_id'                 => ['required', 'integer', 'exists:staffs,id'],
            'date'                     => ['required', 'date_format:Y-m-d'],
        ];
    }

    public function messages(): array
    {
        return [
            'service_id.required' => 'شناسه خدمات الزامی است.',
            'service_id.integer'  => 'شناسه خدمات باید عدد معتبر باشد.',
            'service_id.exists'   => 'خدمت انتخاب شده موجود نیست.',

            'staff_id.required' => 'شناسه کارمند الزامی است.',
            'staff_id.integer'  => 'شناسه کارمند باید عدد معتبر باشد.',
            'staff_id.exists'   => 'کارمند انتخاب شده موجود نیست.',

            'date.required'     => 'تاریخ نوبت الزامی است.',
            'date.date_format'  => 'فرمت تاریخ باید YYYY-MM-DD باشد.',
        ];
    }
}
