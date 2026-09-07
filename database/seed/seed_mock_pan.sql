insert into
    mock_gov_pan (
        aadhaar_number,
        pan_number,
        name,
        dob,
        address
    )
values (
        '123456789012',
        'ABCDE1234F',
        'Ravi Kumar',
        '1990-05-14',
        '12 MG Road, Coimbatore, Tamil Nadu'
    ),
    (
        '234567890123',
        'PQRSX5678K',
        'Priya Sundaram',
        '1995-11-02',
        '45 Anna Nagar, Chennai, Tamil Nadu'
    ) on conflict (aadhaar_number) do nothing;