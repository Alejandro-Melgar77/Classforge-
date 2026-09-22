import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../../core/models/api-response.model';
import { Folder } from '../models/folder.model';

@Injectable({
  providedIn: 'root'
})
export class FoldersService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/folders`;

  getFolderTree(): Observable<ApiResponse<Folder[]>> {
    return this.http.get<ApiResponse<Folder[]>>(`${this.apiUrl}/tree`);
  }
}
