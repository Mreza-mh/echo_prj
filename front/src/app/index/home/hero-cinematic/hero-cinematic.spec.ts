import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HeroCinematic } from './hero-cinematic';

describe('HeroCinematic', () => {
  let component: HeroCinematic;
  let fixture: ComponentFixture<HeroCinematic>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HeroCinematic]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HeroCinematic);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
