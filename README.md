# Sunrise Hospital Management System

A Hospital Management System developed using Frappe Framework v16 and ERPNext v16.

The application manages hospital operations, including patient registration, doctor appointments, consultation billing, medicine procurement, inventory management, inpatient admission, treatment records, final billing and patient discharge.

## Project Information

| Property | Details |
|---|---|
| Project Name | Sunrise Hospital Management System |
| Custom App | hospital_management |
| Module | Sunrise Hospital Management |
| Frappe Version | 16.56.0 |
| ERPNext Version | 16.54.0 |
| App Version | 0.0.1 |
| Python Requirement | 3.14+ |

## Technology Stack

- Frappe Framework
- ERPNext
- Python
- JavaScript
- MariaDB
- HTML
- CSS
- Jinja

## Main Features

### 1. Patient Management
- Patient registration and profile management.
- Patient-to-ERPNext Customer linkage.
- Patient information and allergy validation.
- Emergency contact information.

### 2. Doctor and Department Management
- Hospital department management.
- Doctor registration and department assignment.
- Consultation fee configuration.
- Active and inactive doctor management.

### 3. Doctor Appointment Management
- Appointment booking and scheduling.
- Department-based doctor selection.
- Automatic consultation fee fetching.
- Duplicate appointment prevention.
- Appointment status management.
- Appointment-to-invoice integration.

### 4. Accounting Integration
- ERPNext Sales Invoice integration.
- Automatic draft consultation invoice generation.
- Payment Entry integration.
- Partial payment support.
- Automatic payment status synchronisation.
- Outstanding balance calculation.

### 5. Buying and Procurement
- Supplier management.
- Purchase Order creation.
- Purchase Receipt management.
- Purchase Invoice integration.
- Supplier payment processing.

### 6. Inventory and Pharmacy Management
- Medicine stock management.
- Pharmacy and Ward Store warehouses.
- Batch and expiry tracking.
- Material transfers.
- Medicine consumption management.
- Automatic Material Issue Stock Entry creation.
- Stock restoration through cancellation.

### 7. Low Stock Management
- Warehouse-based reorder levels.
- Automatic Material Request generation.
- Hospital Low Stock Alert notification.
- In-app notification for purchasing staff.

### 8. Patient Admission and Discharge
- Patient admission management.
- Hospital room and bed allocation.
- Bed availability validation.
- Automatic bed occupancy updates.
- Treatment Record management.
- Medicine Usage tracking.
- Room charge calculation.
- Treatment and medicine charge calculation.
- Final admission billing.
- Payment verification.
- Doctor discharge approval.
- Automatic bed release after discharge.

### 9. Public Appointment Booking
- Public appointment booking Web Form.
- Guest-access booking submission.
- Patient and Customer matching or creation.
- Department-based doctor filtering.
- Appointment validation.
- Automatic creation of official Doctor Appointment records.

### 10. Custom Operational Reports

The application includes four custom reports:

1. Doctor Appointment Register
2. Patient Admission & Discharge Register
3. Medicine Usage Register
4. Purchase Order Register

### 11. Custom Print Formats

Three hospital-themed print formats are configured:

1. Sunrise Hospital Appointment Confirmation
2. Sunrise Hospital Final Bill
3. Sunrise Hospital Discharge Summary

## Custom DocTypes

The application contains ten hospital-specific DocTypes:

1. Hospital Department
2. Doctor
3. Patient
4. Doctor Appointment
5. Hospital Room
6. Hospital Bed
7. Patient Admission
8. Treatment Record
9. Medicine Usage
10. Patient Appointment Request

## Application Structure

```text
hospital_management/
│
├── hospital_management/
│   │
│   ├── sunrise_hospital_management/
│   │   └── doctype/
│   │       ├── doctor/
│   │       ├── hospital_department/
│   │       ├── patient/
│   │       ├── doctor_appointment/
│   │       ├── hospital_room/
│   │       ├── hospital_bed/
│   │       ├── patient_admission/
│   │       ├── treatment_record/
│   │       ├── medicine_usage/
│   │       └── patient_appointment_request/
│   │
│   ├── fixtures/
│   │   ├── report.json
│   │   └── print_format.json
│   │
│   ├── hooks.py
│   └── payment_sync.py
│
├── README.md
├── pyproject.toml
└── license.txt
```

## Installation Requirements

- Frappe Framework v16.
- ERPNext v16.
- Python 3.14 or compatible configured environment.
- MariaDB.
- A working Frappe Bench installation.

ERPNext should be installed on the target site before installing this application.

## Installation Guide

### Step 1: Navigate to your Frappe Bench

```bash
cd /path/to/your/frappe-bench
```

### Step 2: Get the application

Replace `sebastianjose1128-source` with the GitHub account that hosts this repository.

```bash
bench get-app https://github.com/sebastianjose1128-source/sunrise-hospital-management-system.git --branch version-16
```

### Step 3: Install the application

Replace `<SITE_NAME>` with your Frappe site name.

```bash
bench --site <SITE_NAME> install-app hospital_management
```

### Step 4: Run migration

```bash
bench --site <SITE_NAME> migrate
```

The application includes selected Report and Print Format fixtures.

## Important Project Notes

- The original assessment was developed and tested on a local Frappe site named sunrise-hospital.localhost.
- The repository contains application source code and selected fixtures, not the original site database.
- Hospital master records, accounting records, stock transactions and demonstration data are not included as a complete database copy.
- The public appointment booking page was tested locally and requires appropriate Web Form and Guest permission configuration on a new site.
- Appointment time choices are predefined and do not use a live availability calendar.
- Patient login and online appointment history are not implemented.
- External payment gateway integration is not implemented.
- Email and SMS notification delivery is not configured.
- The low-stock reorder function and in-app notification were manually tested; daily scheduled execution was not independently verified.
- Reorder thresholds are demonstration values and should be reviewed before real-world use.
- The combined treatment and medicine admission billing scenario was not completed as a final-bill demonstration.

## Project Purpose

This project demonstrates the development of a hospital operations management application using Frappe Framework and ERPNext.

It integrates hospital-specific DocTypes, Python controllers, JavaScript form behaviour, accounting transactions, inventory management, workflow automation, custom operational reports, print formats and public appointment booking.

## License

MIT