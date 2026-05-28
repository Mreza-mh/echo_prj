<?php

namespace App\Http\Controllers;

use App\Http\Requests\Resource\ResourceFilterRequest;
use App\Http\Requests\Resource\ResourceCreateRequest;
use App\Http\Requests\Resource\ResourceEditRequest;
use App\Http\Responses\ApiResponse;
use App\Services\ResourceService;

class ResourceController
{
    protected ResourceService $resourceService;

    public function __construct(ResourceService $resourceService)
    {
        $this->resourceService = $resourceService;
    }

    /**
     * @OA\Post(
     *     path="/resource/list",
     *     tags={"Resource"},
     *     summary="دریافت لیست منابع",
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="is_paginate", type="boolean", example=true),
     *             @OA\Property(property="count_item", type="integer", example=10),
     *             @OA\Property(property="resource_name", type="string", example="دستگاه اکسیژن"),
     *             @OA\Property(property="resource_type", type="string", example="Medical")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="لیست منابع با موفقیت دریافت شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="لیست منابع با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="array", @OA\Items(type="object"))
     *         )
     *     )
     * )
     */
    public function getResourceList(ResourceFilterRequest $request)
    {
        $result = $this->resourceService->getResourceList($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Get(
     *     path="/resource/{resource_id}",
     *     tags={"Resource"},
     *     summary="دریافت جزئیات یک منبع",
     *     @OA\Parameter(
     *         name="resource_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="منبع با موفقیت دریافت شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="منبع با موفقیت دریافت شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function getResource($resource_id)
    {
        $result = $this->resourceService->getResource($resource_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Post(
     *     path="/resource/add",
     *     tags={"Resource"},
     *     summary="افزودن منبع جدید",
     *     @OA\RequestBody(
     *         required=true,
     *         @OA\JsonContent(
     *             required={"resource_name","resource_type"},
     *             @OA\Property(property="resource_name", type="string", example="دستگاه اکسیژن"),
     *             @OA\Property(property="resource_type", type="string", example="Medical")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="منبع با موفقیت افزوده شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="منبع با موفقیت افزوده شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function addResource(ResourceCreateRequest $request)
    {
        $result = $this->resourceService->addResource($request);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Patch(
     *     path="/resource/edit/{resource_id}",
     *     tags={"Resource"},
     *     summary="ویرایش منبع",
     *     @OA\Parameter(
     *         name="resource_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\RequestBody(
     *         required=false,
     *         @OA\JsonContent(
     *             @OA\Property(property="resource_name", type="string", example="دستگاه اکسیژن پیشرفته"),
     *             @OA\Property(property="resource_type", type="string", example="Medical")
     *         )
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="منبع با موفقیت ویرایش شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="منبع با موفقیت ویرایش شد"),
     *             @OA\Property(property="data", type="object")
     *         )
     *     )
     * )
     */
    public function editResource(ResourceEditRequest $request, $resource_id)
    {
        $result = $this->resourceService->editResource($request, $resource_id);
        return ApiResponse::success($result['data'], $result['message']);
    }

    /**
     * @OA\Delete(
     *     path="/resource/delete/{resource_id}",
     *     tags={"Resource"},
     *     summary="حذف منبع",
     *     @OA\Parameter(
     *         name="resource_id",
     *         in="path",
     *         required=true,
     *         @OA\Schema(type="integer")
     *     ),
     *     @OA\Response(
     *         response=200,
     *         description="منبع با موفقیت حذف شد",
     *         @OA\JsonContent(
     *             @OA\Property(property="success", type="boolean", example=true),
     *             @OA\Property(property="message", type="string", example="منبع با موفقیت حذف شد"),
     *             @OA\Property(property="data", type="object", example=null)
     *         )
     *     )
     * )
     */
    public function deleteResource($resource_id)
    {
        $result = $this->resourceService->deleteResource($resource_id);
        return ApiResponse::success($result['data'], $result['message']);
    }
}
