import { Component } from '@angular/core';
import { CredentialsService } from './credentials.service';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss'
})
export class AuthComponent {
  constructor(private credentials:CredentialsService){



  }
}
