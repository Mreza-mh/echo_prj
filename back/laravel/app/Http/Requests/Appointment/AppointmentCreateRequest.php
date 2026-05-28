<?php

namespace App\Http\Requests\Appointment;

use Illuminate\Foundation\Http\FormRequest;
use App\Enums\ReservationType; // فرض: یک Enum برای Online, Phone, Special

class AppointmentCreateRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            // مطابق با نام فیلد در مدل Appointment
            'user_id'                  => ['required', 'integer', 'exists:users,id'],
            'staff_id'                 => ['required', 'integer', 'exists:staffs,id'],
            // مطابق با نام فیلد در مدل OrganizationService
            'service_id' => ['required', 'integer', 'exists:services,id'],
            // مطابق با نام فیلد در مدل Appointment
            'date_of_turn'             => ['required', 'date_format:Y-m-d'],
            'start_time'               => ['required', 'date_format:H:i'], // 24-hour format (HH:MM)
            'type'                     => ['nullable', 'in:' . implode(',', ReservationType::values())], // Online, Phone, Special
            // مطابق با نام فیلد در مدل Appointment
            'permissible_interference' => ['nullable', 'boolean'],
            'resource_ids'             => ['nullable', 'array'],
            'resource_ids.*'           => ['integer', 'exists:resources,id'],
        ];
    }

    public function messages(): array
    {
        return [
            'user_id.required'                  => 'شناسه مشتری (کاربر) الزامی است.',
            'user_id.integer'                   => 'شناسه مشتری (کاربر) باید عدد باشد.',
            'staff_id.required'                 => 'شناسه کارمند الزامی است.',
            'staff_id.integer'                  => 'شناسه کارمند باید عدد باشد.',
            'service_id.required'               => 'شناسه خدمات الزامی است.',
            'service_id.integer'                => 'شناسه خدمات باید عدد باشد.',
            'date_of_turn.required'             => 'تاریخ نوبت الزامی است.',
            'start_time.required'               => 'ساعت شروع نوبت الزامی است.',
            'type.in'                           => 'نوع رزرو معتبر نیست.',
            'resource_ids.*.integer'            => 'شناسه منبع باید عدد باشد.',
        ];
    }
}
