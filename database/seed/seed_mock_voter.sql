insert into
    mock_gov_voter (
        aadhaar_number,
        voter_id,
        name,
        dob,
        address
    )
values (
        '123456789012',
        'TN1234567890',
        'Ravi Kumar',
        '1990-05-14',
        '12 MG Road, Coimbatore, Tamil Nadu'
    ),
    (
        '345678901234',
        'TN9876543210',
        'Arun Vel',
        '1988-03-21',
        '7 Race Course Road, Coimbatore, Tamil Nadu'
    ) on conflict (aadhaar_number) do nothing;