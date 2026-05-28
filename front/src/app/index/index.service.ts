import { Injectable } from '@angular/core';
import { IndexHttpService } from './index-http.service';
import { HttpRequest } from '@angular/common/http';

/**
 * dont use --GenericHttpService-- in this class
 * use when need use "pipe" or "map" in your service
 */

@Injectable({
  providedIn: 'root',
})
export class IndexService {

  constructor(private indexHttpService: IndexHttpService) {}


}
