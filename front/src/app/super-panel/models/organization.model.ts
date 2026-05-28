export interface Organization {
  id: string;
  name: string;
  business_type: string;
  address: string;
  phone: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateOrganizationRequest {
  name: string;
  business_type: string;
  address: string;
  phone: string;
}

export interface UpdateOrganizationRequest extends Partial<CreateOrganizationRequest> {
  id: string;
}

export interface OrganizationFilterRequest {
  is_paginate?: boolean;
  count_item?: number;
  name?: string;
  business_type?: string;
  address?: string;
  phone?: string;
  search?: string; // For backward compatibility
  page?: number;
  per_page?: number;
}