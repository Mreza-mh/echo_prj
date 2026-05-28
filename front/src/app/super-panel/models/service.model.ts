export interface Service {
  id: number;
  title: string;
  default_duration: string; // HH:mm:ss
  general_price: number;
  created_at?: string;
  updated_at?: string;
}

export interface CreateServiceRequest {
  title: string;
  default_duration: string; // HH:mm:ss
  general_price: number;
}

export interface UpdateServiceRequest extends Partial<CreateServiceRequest> {
  id: number;
}

export interface ServiceFilterRequest {
  title?: string;
  is_paginate?: boolean;
  count_item?: number;
  page?: number;
}