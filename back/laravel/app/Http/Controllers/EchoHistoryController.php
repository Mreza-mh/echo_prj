<?php

namespace App\Http\Controllers;

use App\Http\Responses\ApiResponse;
use App\Services\EchoHistoryService;

class EchoHistoryController extends Controller
{
    protected EchoHistoryService $echoHistoryService;
    public function __construct(EchoHistoryService $echoHistoryService){
        $this->echoHistoryService = $echoHistoryService;
    }

    /**
     * @OA\Get(
     *     path="/echo-history/info-doctor/{patient_id}",
     *     tags={"EchoHistory"},
     *     summary="دریافت اطلاعات اکوی بیمار توسط پزشک",
     *     description="پزشک می‌تواند اطلاعات اکوی بیمار را با استفاده از شناسه بیمار دریافت کند.",
     *     security={{"bearerAuth":{}}},
     *
     *     @OA\Parameter(
     *         name="patient_id",
     *         in="path",
     *         required=true,
     *         description="شناسه بیمار",
     *         @OA\Schema(type="integer", example=25)
     *     ),
     *
     *     @OA\Response(
     *         response=200,
     *         description="اطلاعات اکوی بیمار با موفقیت ارسال شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="اطلاعات اکو بیمار با موفقیت ارسال شد"),
     *             @OA\Property(
     *                 property="data",
     *                 type="object",
     *                 example={
     *                     "patient_id": "25",
     *                     "name": "علی احمدی",
     *                     "echo_date": "2024-01-12",
     *                     "details": "Normal EF"
     *                 }
     *             )
     *         )
     *     ),
     *
     *     @OA\Response(
     *         response=404,
     *         description="اکوی بیمار وجود ندارد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=false),
     *             @OA\Property(property="message", type="string", example="اکوی بیمار وجود ندارد")
     *         )
     *     )
     * )
     */

    public function getInfoByDoctor($patient_id){
        $data = $this->echoHistoryService->getInfo($patient_id);
        return ApiResponse::success($data['data'],$data['message']);
    }

    /**
     * @OA\Get(
     *     path="/echo-history/info",
     *     tags={"EchoHistory"},
     *     summary="دریافت اطلاعات اکوی بیمار لاگین شده",
     *     description="این متد اطلاعات اکوی بیمار لاگین شده را بر اساس شناسه کاربر احراز هویت شده دریافت می‌کند.",
     *     security={{"bearerAuth":{}}},
     *
     *     @OA\Response(
     *         response=200,
     *         description="اطلاعات اکوی بیمار با موفقیت ارسال شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="اطلاعات اکو بیمار با موفقیت ارسال شد"),
     *             @OA\Property(
     *                 property="data",
     *                 type="object",
     *                 example={
     *                     "patient_id": "6473af5c0bfa8120c935dc1b",
     *                     "name": "علی احمدی",
     *                     "echo_date": "2024-01-12",
     *                     "details": "Normal EF"
     *                 }
     *             )
     *         )
     *     ),
     *
     *     @OA\Response(
     *         response=404,
     *         description="اکوی بیمار وجود ندارد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=false),
     *             @OA\Property(property="message", type="string", example="اکوی بیمار وجود ندارد")
     *         )
     *     )
     * )
     */
    public function getInfo(){
        $data = $this->echoHistoryService->getInfo();
        return ApiResponse::success($data['data'],$data['message']);
    }

    /**
     * @OA\Get(
     *     path="/echo-history/file/{address}",
     *     tags={"EchoHistory"},
     *     summary="دریافت فایل اکو بیمار",
     *     description="این متد فایل مربوط به اکوی بیمار (تصویر یا PDF) را بر اساس مسیر فایل (`address`) از پوشه public/echos ارسال می‌کند.",
     *     @OA\Parameter(
     *         name="address",
     *         in="path",
     *         required=true,
     *         description="مسیر فایل مورد نظر برای دانلود یا مشاهده",
     *         @OA\Schema(type="string", example="patient_123/report.pdf")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="فایل مورد نظر با موفقیت ارسال شد (توسط response()->file)",
     *         @OA\MediaType(
     *             mediaType="application/octet-stream"
     *         )
     *     ),
     *     @OA\Response(
     *         response=400,
     *         description="مسیر فایل نامعتبر است",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=false),
     *             @OA\Property(property="message", type="string", example="Invalid file path")
     *         )
     *     ),
     *     @OA\Response(
     *         response=404,
     *         description="فایل یافت نشد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=false),
     *             @OA\Property(property="message", type="string", example="File not found")
     *         )
     *     )
     * )
     */
    public function getFile($address){
        $file = $this->echoHistoryService->getFile($address);
        return response()->file($file);
    }
}
