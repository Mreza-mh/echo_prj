<?php

namespace App\Http\Controllers;

use App\Http\Requests\Expertise\ExpertiseCreateRequest;
use App\Http\Requests\Expertise\ExpertiseEditRequest;
use App\Http\Requests\Expertise\ExpertiseFilterRequest;
use App\Http\Responses\ApiResponse;
use App\Services\ExpertiseService;

class ExpertiseController
{
    protected ExpertiseService $expertiseService;

    public function __construct(ExpertiseService $service)
    {
        $this->expertiseService = $service;
    }

    /**
     * @OA\Post(
     *     path="/expertise/list",
     *     tags={"Expertise"},
     *     summary="دریافت لیست تخصص‌ها",
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="is_paginate", type="boolean", example=true),
     *             @OA\Property(property="count_item", type="integer", example=10),
     *             @OA\Property(property="title", type="string", example="Cardiology"),
     *             @OA\Property(property="label", type="string", example="قلب و عروق")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="لیست تخصص‌ها با موفقیت بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="array", @OA\Items(type="object"))
     *         )
     *     )
     * )
     */
    public function getExpertiseList(ExpertiseFilterRequest $request)
    {
        $result = $this->expertiseService->getExpertiseList($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Get(
     *     path="/expertise/{expertise_id}",
     *     tags={"Expertise"},
     *     summary="دریافت جزئیات یک تخصص",
     *     @OA\Parameter(
     *         name="expertise_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="جزئیات تخصص بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function getExpertise($expertise_id)
    {
        $result = $this->expertiseService->getExpertise($expertise_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/expertise/add",
     *     tags={"Expertise"},
     *     summary="افزودن تخصص جدید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"title","label"},
     *             @OA\Property(property="title", type="string", example="Cardiology"),
     *             @OA\Property(property="label", type="string", example="قلب و عروق")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="تخصص با موفقیت اضافه شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function addExpertise(ExpertiseCreateRequest $request)
    {
        $result = $this->expertiseService->addExpertise($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Patch(
     *     path="/expertise/edit/{expertise_id}",
     *     tags={"Expertise"},
     *     summary="ویرایش تخصص",
     *     @OA\Parameter(
     *         name="expertise_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             @OA\Property(property="title", type="string", example="Cardiology"),
     *             @OA\Property(property="label", type="string", example="قلب و عروق")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="تخصص با موفقیت ویرایش شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function editExpertise(ExpertiseEditRequest $request, $expertise_id)
    {
        $result = $this->expertiseService->editExpertise($request, $expertise_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Delete(
     *     path="/expertise/delete/{expertise_id}",
     *     tags={"Expertise"},
     *     summary="حذف تخصص",
     *     @OA\Parameter(
     *         name="expertise_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="تخصص با موفقیت حذف شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function deleteExpertise($expertise_id)
    {
        $result = $this->expertiseService->deleteExpertise($expertise_id);
        return ApiResponse::success($result['data'], $result['message']);
    }
}
