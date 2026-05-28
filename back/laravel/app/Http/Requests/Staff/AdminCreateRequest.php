<?php

namespace App\Http\Requests\Staff;

use App\Enums\StaffRoleType;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Validation\Rule;

class AdminCreateRequest extends FormRequest
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
            'organization_id' => ['required', 'uuid', 'exists:organizations,id'],
            'user_id'         => ['required', 'integer', 'exists:users,id'],
        ];
    }

    public function messages(): array
    {
        return [
            'organization_id.required' => 'شناسه سازمان الزامی است.',
            'organization_id.uuid'     => 'شناسه سازمان معتبر نیست.',
            'organization_id.exists'   => 'سازمان مورد نظر وجود ندارد.',

            'user_id.required'         => 'شناسه کاربر الزامی است.',
            'user_id.integer'          => 'شناسه کاربر باید عدد باشد.',
            'user_id.exists'           => 'کاربر انتخاب‌شده معتبر نیست.',
        ];
    }
}
