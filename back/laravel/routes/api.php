<?php


use App\Http\Controllers\AppointmentController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\EchoHistoryController;
use App\Http\Controllers\ExpertiseController;
use App\Http\Controllers\ResourceController;
use App\Http\Controllers\ServiceController;
use App\Http\Controllers\StaffController;
use App\Http\Controllers\StatusController;
use App\Http\Controllers\AIChatController;
use App\Http\Controllers\PatientReportController;
use Illuminate\Support\Facades\Route;


Route::post('ai/chat', [AIChatController::class, 'chat']);

// Patient Data Routes
Route::post('patient-profile/store', [\App\Http\Controllers\PatientDataController::class, 'store']);
Route::get('patient-profile/{user_id}', [\App\Http\Controllers\PatientDataController::class, 'show']);

Route::group(['prefix' => 'auth'], function () {
    Route::post('send/verification', [AuthController::class, 'sendVerificationCode']);
    Route::post('login/verification', [AuthController::class, 'loginWithVerificationCode']);
    Route::post('login/password', [AuthController::class, 'loginWithPassword']);
    Route::put('set/password', [AuthController::class, 'setPassword'])->middleware('auth:api');
    Route::get('get/me', [AuthController::class, 'getMe'])->middleware('auth:api');
    Route::get('verify/{user_id}', [AuthController::class, 'verifyUser'])->middleware('auth:api');
    Route::post('change-password', [AuthController::class, 'changePassword'])->middleware('auth:api');
    Route::post('forget-password', [AuthController::class, 'forgetPassword']);
    Route::put('edit/profile', [AuthController::class, 'editProfile'])->middleware('auth:api');
    Route::post('list-user', [AuthController::class, 'listUsers'])->middleware('auth:api');
});

Route::group(['prefix' => 'service'], function () {
    Route::post('list',[ServiceController::class,'getServiceList']);
    Route::get('{service_id}',[ServiceController::class,'getService'])->middleware('auth:api');
    Route::post('add',[ServiceController::class,'addService'])->middleware('auth:api');
    Route::patch('edit/{service_id}',[ServiceController::class,'editService'])->middleware('auth:api');
    Route::delete('delete/{service_id}',[ServiceController::class,'deleteService'])->middleware('auth:api');
});

Route::group(['prefix' => 'staff'], function () {
    Route::post('list', [StaffController::class, 'getStaffList'])->middleware('auth:api');
    Route::get('{staff_id}', [StaffController::class, 'getStaff'])->middleware('auth:api');
    Route::post('add', [StaffController::class, 'addStaff'])->middleware('auth:api');
    Route::patch('edit/{staff_id}', [StaffController::class, 'editStaff'])->middleware('auth:api');
    Route::delete('delete/{staff_id}', [StaffController::class, 'deleteStaff'])->middleware('auth:api');
});
Route::group(['prefix' => 'staff-schedule'], function () {
    Route::post('list', [StaffController::class, 'getStaffList'])->middleware('auth:api');
    Route::post('add/{staff_id}', [StaffController::class, 'addStaffSchedule'])->middleware('auth:api');
});

Route::group(['prefix' => 'resource'], function () {
    Route::post('list', [ResourceController::class, 'getResourceList'])->middleware('auth:api');
    Route::get('{resource_id}', [ResourceController::class, 'getResource'])->middleware('auth:api');
    Route::post('add', [ResourceController::class, 'addResource'])->middleware('auth:api');
    Route::patch('edit/{resource_id}', [ResourceController::class, 'editResource'])->middleware('auth:api');
    Route::delete('delete/{resource_id}', [ResourceController::class, 'deleteResource'])->middleware('auth:api');
});

Route::group(['prefix' => 'status'], function () {
    Route::post('list', [StatusController::class, 'getStatusList'])->middleware('auth:api');
    Route::get('{status_id}', [StatusController::class, 'getStatus'])->middleware('auth:api');
    Route::post('add', [StatusController::class, 'addStatus'])->middleware('auth:api');
    Route::patch('edit/{status_id}', [StatusController::class, 'editStatus'])->middleware('auth:api');
    Route::delete('delete/{status_id}', [StatusController::class, 'deleteStatus'])->middleware('auth:api');
});

Route::group(['prefix' => 'expertise'], function () {
    Route::post('list', [ExpertiseController::class, 'getExpertiseList'])->middleware('auth:api');
    Route::get('{expertise_id}', [ExpertiseController::class, 'getExpertise'])->middleware('auth:api');
    Route::post('add', [ExpertiseController::class, 'addExpertise'])->middleware('auth:api');
    Route::patch('edit/{expertise_id}', [ExpertiseController::class, 'editExpertise'])->middleware('auth:api');
    Route::delete('delete/{expertise_id}', [ExpertiseController::class, 'deleteExpertise'])->middleware('auth:api');
});

Route::group(['prefix' => 'appointment'], function () {
    Route::post('get-available-slots', [AppointmentController::class, 'getAvailableSlots'])->middleware('auth:api');
    Route::post('add-appointment', [AppointmentController::class, 'addAppointment'])->middleware('auth:api');
    Route::patch('edit-appointment/{id}', [AppointmentController::class, 'editAppointment'])->middleware('auth:api');
    Route::get('get-appointment/{id}', [AppointmentController::class, 'getAppointment'])->middleware('auth:api');
    Route::post('get-calendar-dashboard', [AppointmentController::class, 'getCalendarDashboard'])->middleware('auth:api');
    Route::get('get-current-appointment', [AppointmentController::class, 'getCurrentAppointment'])->middleware('auth:api');
    Route::post('list', [AppointmentController::class, 'listAppointments'])->middleware('auth:api');

});

Route::group(['prefix' => 'ai'], function () {
    Route::post('chat', [AIChatController::class, 'chat'])->middleware('auth:api');
});

Route::group(['prefix' => 'echo-history'], function () {
    Route::get('info-doctor/{patient_id}', [EchoHistoryController::class, 'getInfoByDoctor'])->middleware('auth:api');
    Route::get('info', [EchoHistoryController::class, 'getInfo'])->middleware('auth:api');
    Route::get('file/{address}', [EchoHistoryController::class, 'getFile'])->where('address', '.*');
});

// Patient Report Routes (گزارش‌های نهایی اکو)
Route::group(['prefix' => 'patient-report'], function () {
    // دریافت لیست ویزیت‌های یک بیمار
    Route::get('visits/{patient_id}', [PatientReportController::class, 'getPatientVisits'])->middleware('auth:api');
    
    // دریافت گزارش کامل یک ویزیت خاص
    Route::get('report/{patient_id}/{visit_date}', [PatientReportController::class, 'getPatientReport'])->middleware('auth:api');
    
    // دریافت فقط متن گزارش (برای نمایش سریع)
    Route::get('text/{patient_id}/{visit_date}', [PatientReportController::class, 'getReportText'])->middleware('auth:api');
    
    // نمایش گزارش HTML (بدون نیاز به احراز هویت برای نمایش در مرورگر)
    Route::get('html/{patient_id}/{visit_date}', [PatientReportController::class, 'showHtmlReport']);
    
    // دریافت خلاصه وضعیت بیمار (برای داشبورد)
    Route::get('summary/{patient_id}', [PatientReportController::class, 'getPatientSummary'])->middleware('auth:api');
});

Route::get('/api-docs', function () {
    $path = storage_path('api-docs/api-docs.json');

    if (!file_exists($path)) {
        return response()->json(['error' => 'Swagger file not found'], 404);
    }

    return response()->file($path, [
        'Content-Type' => 'application/json'
    ]);

});




