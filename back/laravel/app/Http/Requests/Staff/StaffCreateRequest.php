<?php

namespace App\Http\Requests\Staff;

use App\Enums\StaffRoleType;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Validation\Rule;

class StaffCreateRequest extends FormRequest
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
            'user_id'         => ['required', 'integer', 'exists:users,id'],
            'expertise_id'    => ['required', 'integer', 'exists:expertises,id'],

        ];
    }

    public function messages(): array
    {
        return [
            'user_id.required'         => 'شناسه کاربر الزامی است.',
            'user_id.integer'          => 'شناسه کاربر باید عدد باشد.',
            'user_id.exists'           => 'کاربر انتخاب‌شده معتبر نیست.',

            'expertise_id.required'    => 'شناسه تخصص الزامی است.',
            'expertise_id.integer'     => 'شناسه تخصص باید عدد باشد.',
            'expertise_id.exists'      => 'تخصص انتخاب‌شده معتبر نیست.',




        ];
    }
}
