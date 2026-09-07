insert into
    mock_gov_udyam (
        aadhaar_number,
        udyam_number,
        name,
        dob,
        address
    )
values (
        '345678901234',
        'UDYAM-TN-01-0012345',
        'Arun Vel',
        '1988-03-21',
        '7 Race Course Road, Coimbatore, Tamil Nadu'
    ) on conflict (aadhaar_number) do nothing;