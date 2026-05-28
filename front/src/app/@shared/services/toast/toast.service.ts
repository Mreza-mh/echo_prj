import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class ToastService {

  constructor(private snackBar: MatSnackBar) {}

  success(message: string, duration: number = 3000) {
    this.snackBar.open(message, 'Close', {
      duration: duration,
      panelClass: ['snackbar-success']
    });
  }

  error(message: string, duration: number = 5000) {
    this.snackBar.open(message, 'Close', {
      duration: duration,
      panelClass: ['snackbar-error']
    });
  }

  warn(message: string, duration: number = 4000) {
    this.snackBar.open(message, 'Close', {
      duration: duration,
      panelClass: ['snackbar-warn']
    });
  }
}
