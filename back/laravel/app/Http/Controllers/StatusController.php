<?php

namespace App\Http\Controllers;

use App\Http\Requests\Status\StatusFilterRequest;
use App\Http\Requests\Status\StatusCreateRequest;
use App\Http\Requests\Status\StatusEditRequest;
use App\Http\Responses\ApiResponse;
use App\Services\StatusService;

class StatusController
{
    protected StatusService $statusService;

    public function __construct(StatusService $statusService)
    {
        $this->statusService = $statusService;
    }

    /**
     * @OA\Post(
     *     path="/status/list",
     *     tags={"Status"},
     *     summary="دریافت لیست وضعیت‌ها",
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="is_paginate", type="boolean", example=true),
     *             @OA\Property(property="count_item", type="integer", example=10),
     *             @OA\Property(property="title", type="string", example="Active"),
     *             @OA\Property(property="label", type="string", example="فعال")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="لیست وضعیت‌ها بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="array", @OA\Items(type="object"))
     *         )
     *     )
     * )
     */
    public function getStatusList(StatusFilterRequest $request)
    {
        $result = $this->statusService->getStatusList($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Get(
     *     path="/status/{status_id}",
     *     tags={"Status"},
     *     summary="دریافت جزئیات یک وضعیت",
     *     @OA\Parameter(
     *         name="status_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="جزئیات وضعیت بازگشت داده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function getStatus($status_id)
    {
        $result = $this->statusService->getStatus($status_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/status/add",
     *     tags={"Status"},
     *     summary="افزودن وضعیت جدید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"title","label"},
     *             @OA\Property(property="title", type="string", example="Active"),
     *             @OA\Property(property="label", type="string", example="فعال")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="وضعیت اضافه شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function addStatus(StatusCreateRequest $request)
    {
        $result = $this->statusService->addStatus($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Patch(
     *     path="/status/edit/{status_id}",
     *     tags={"Status"},
     *     summary="ویرایش یک وضعیت",
     *     @OA\Parameter(
     *         name="status_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="title", type="string", example="Inactive"),
     *             @OA\Property(property="label", type="string", example="غیرفعال")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="وضعیت ویرایش شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function editStatus(StatusEditRequest $request, $status_id)
    {
        $result = $this->statusService->editStatus($request, $status_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Delete(
     *     path="/status/delete/{status_id}",
     *     tags={"Status"},
     *     summary="حذف یک وضعیت",
     *     @OA\Parameter(
     *         name="status_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="وضعیت حذف شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="عملیات موفق"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function deleteStatus($status_id)
    {
        $result = $this->statusService->deleteStatus($status_id);
        return ApiResponse::success($result['data'], $result['message']);
    }
}

