STATE_OPTIONS = {
    "Auroria": {
        "description": "A vibrant coastal state with a high cost of living and a booming tech sector.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Undeveloped Marsh Land",
            "Coastal Capital",
            "Suburban Sprawl",
            "Downtown Core"
        ],
        "land_cost_modifier": 1.5,
        "property_tax": 2.0,
        "minimum_wage": 15,
        "population": 10000000,
        "population_density": 1200,
        "infrastructure_spending": "High",
        "coastal": True,
        "median_salary": 70000,
        "natural_disaster_chance": 0.1
    },
    "Deltora": {
        "description": "A rural, landlocked state known for its expansive farmlands and affordable land prices.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Undeveloped Marsh Land",
            "Industrial Valley",
            "Suburban Sprawl",
            "Rural Retreat",
            "Mountain Foothills"
        ],
        "land_cost_modifier": 0.8,
        "property_tax": 1.2,
        "minimum_wage": 10,
        "population": 5000000,
        "population_density": 50,
        "infrastructure_spending": "Low",
        "coastal": False,
        "median_salary": 40000,
        "natural_disaster_chance": 0.2
    },
    "Neonix": {
        "description": "A modern, urbanized coastal state with high property taxes and a booming tech sector.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Downtown Core",
            "Suburban Sprawl",
            "Coastal Capital"
        ],
        "land_cost_modifier": 2.0,
        "property_tax": 3.0,
        "minimum_wage": 20,
        "population": 15000000,
        "population_density": 5000,
        "infrastructure_spending": "Very High",
        "coastal": True,
        "median_salary": 90000,
        "natural_disaster_chance": 0.05
    },
    "Veridia": {
        "description": "A green, sustainability-focused state with moderate costs and a mix of urban and rural areas.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Undeveloped Marsh Land",
            "Idealistic Island",  # Only available in states that allow coastal or island options.
            "Industrial Valley",
            "Rural Retreat",
            "Mountain Foothills"
        ],
        "land_cost_modifier": 1.0,
        "property_tax": 1.5,
        "minimum_wage": 12,
        "population": 8000000,
        "population_density": 200,
        "infrastructure_spending": "Medium",
        "coastal": False,
        "median_salary": 60000,
        "natural_disaster_chance": 0.15
    },
    "Caldora": {
        "description": "A highly industrialized, densely populated coastal state with premium land prices and robust infrastructure.",
        "allowed_land_options": [
            "Your Parents' Garage",
            "Coastal Capital",
            "Downtown Core",
            "Suburban Sprawl",
            "Industrial Valley"
        ],
        "land_cost_modifier": 2.5,
        "property_tax": 3.5,
        "minimum_wage": 22,
        "population": 20000000,
        "population_density": 6000,
        "infrastructure_spending": "Very High",
        "coastal": True,
        "median_salary": 100000,
        "natural_disaster_chance": 0.08
    }
}


LAND_OPTIONS = {
    "Your Parents' Garage": {
        "cost": 500,  # very low cost
        "developable_land": 0,
        "development_cost_multiplier": 1.0,
        "base_employee_cap": 2,
        "description": "The humble beginnings! Your parents offered to pay—but there's no developable land here. Limited capacity for growth."
    },
    "Undeveloped Marsh Land": {
        "cost": 30000,  # relatively low cost compared to island land
        "developable_land": 50,
        "development_cost_multiplier": 1.5,
        "base_employee_cap": 20,
        "description": "Cheap land with a lot of potential—but also many challenges, such as flooding, mosquitoes, and high development costs."
    },
    "Idealistic Island": {
        "cost": 90000,  # higher cost than marsh even with same developable land
        "developable_land": 50,
        "development_cost_multiplier": 1.5,
        "base_employee_cap": 50,
        "description": "A picturesque island offering unique charm. Pros: Scenic views and lifestyle perks. Cons: Isolation and higher purchase cost."
    },
    "Industrial Valley": {
        "cost": 120000,
        "developable_land": 300,
        "development_cost_multiplier": 0.75,
        "base_employee_cap": 100,
        "description": "A rugged industrial area famous for low regulations and abundant materials. Pros: Cost-effective operations. Cons: Less attractive for top talent."
    },
    "Coastal Capital": {
        "cost": 200000,
        "developable_land": 400,
        "development_cost_multiplier": 1.0,
        "base_employee_cap": 150,
        "description": "A bustling coastal metropolis with prestige and excellent connectivity—but at a premium price."
    },
    "Suburban Sprawl": {
        "cost": 80000,
        "developable_land": 200,
        "development_cost_multiplier": 1.2,
        "base_employee_cap": 60,
        "description": "A sprawling suburban area offering a balance between cost and growth potential. Pros: Affordable and spacious. Cons: Moderate infrastructure."
    },
    "Downtown Core": {
        "cost": 180000,
        "developable_land": 350,
        "development_cost_multiplier": 1.3,
        "base_employee_cap": 130,
        "description": "Prime downtown real estate with excellent connectivity and prestige—but space is limited and costs are high."
    },
    "Rural Retreat": {
        "cost": 40000,
        "developable_land": 100,
        "development_cost_multiplier": 0.8,
        "base_employee_cap": 30,
        "description": "A quiet rural area with very low costs but a limited talent pool and fewer amenities."
    },
    "Mountain Foothills": {
        "cost": 60000,
        "developable_land": 120,
        "development_cost_multiplier": 1.0,
        "base_employee_cap": 40,
        "description": "Scenic land in the mountain foothills with moderate development challenges and a unique environment."
    }
}

office_options = {
    "hole-in-the-wall": {
        "cost": 100000,
        "build_time": 10,
        "additional_employee_cap": 50,
        "land_usage": 0,
        "description": "A modest, cramped space in an existing facility, with minimal new construction."
    },
    "office suite": {
        "cost": 250000,
        "build_time": 20,
        "additional_employee_cap": 100,
        "land_usage": 10,
        "description": "Shared office space with modern amenities, ideal for small teams."
    },
    "small office building": {
        "cost": 500000,
        "build_time": 30,
        "additional_employee_cap": 200,
        "land_usage": 50,
        "description": "A dedicated small office building for growing companies."
    },
    "warehouse": {
        "cost": 750000,
        "build_time": 45,
        "additional_employee_cap": 150,
        "land_usage": 40,
        "description": "A large warehouse suited for companies with significant logistics needs."
    },
    "wide campus": {
        "cost": 2000000,
        "build_time": 60,
        "additional_employee_cap": 500,
        "land_usage": 200,
        "description": "A sprawling campus with multiple buildings, ideal for corporate giants."
    },
    "skyscraper": {
        "cost": 3000000,
        "build_time": 90,
        "additional_employee_cap": 1000,
        "land_usage": 150,
        "description": "A towering skyscraper that maximizes vertical space, requiring less land area but high construction complexity."
    }
}

CORPORATE_CATEGORIES = {
    "Consumer Goods": {
        "description": "Companies that manufacture products used by everyday consumers.",
        "subcategories": {
            "Food & Beverage": {
                "description": "Producers of food, drinks, and related consumables."
            },
            "Apparel": "Companies in clothing, footwear, and accessories.",
            "Household Products": "Manufacturers of appliances and home care products.",
            "Recreation": "Any product designed to be used in a recreational setting."
        }
    },
    "Technology": {
        "description": "Firms operating in the tech sector, from hardware to software.",
        "subcategories": {
            "Software": "Developers of applications, operating systems, and cloud services.",
            "Hardware": "Producers of computers, smartphones, and peripherals.",
            "Semiconductors": "Companies involved in chip manufacturing and related technology."
        }
    },
    "Entertainment": {
        "description": "Companies that create or distribute content for entertainment.",
        "subcategories": {
            "Film & Television": "Studios and production companies.",
            "Music": "Record labels, artists, and streaming platforms.",
            "Gaming": "Video game developers and publishers."
        }
    },
    "Services": {
        "description": "Firms that offer services rather than physical products.",
        "subcategories": {
            "Legal Services": "Law firms, legal advisors, and related consultancies.",
            "Financial Services": "Banks, insurance companies, investment firms, and fintech.",
            "Transportation": "Taxi, rideshare, logistics, and courier services.",
            "Hospitality": "Hotels, restaurants, and event management companies.",
            "Personal Care": "Salons, spas, fitness centers, and wellness providers."
        }
    },
    "Retail": {
        "description": "Companies that sell goods directly to consumers.",
        "subcategories": {
            "Department Stores": "Large-scale retailers with multiple product lines.",
            "E-commerce": "Online retail businesses and marketplaces.",
            "Specialty Retail": "Boutique stores and niche product sellers."
        }
    },
    "Finance": {
        "description": "Institutions and firms offering financial products and services.",
        "subcategories": {
            "Banking": "Traditional banks, credit unions, and commercial lenders.",
            "Investment": "Investment banks, hedge funds, and private equity firms.",
            "Insurance": "Companies offering insurance and risk management services."
        }
    },
    "Healthcare": {
        "description": "Companies in the healthcare and life sciences sectors.",
        "subcategories": {
            "Pharmaceuticals": "Drug manufacturers and distributors.",
            "Biotechnology": "Biotech companies focused on research and development.",
            "Medical Devices": "Producers of medical equipment and devices.",
            "Healthcare Services": "Hospitals, clinics, and healthcare providers."
        }
    },
    "Energy": {
        "description": "Firms involved in the production and distribution of energy.",
        "subcategories": {
            "Oil & Gas": "Exploration, production, and refining companies.",
            "Renewable Energy": "Solar, wind, hydro, and other renewable sources."
        }
    },
    "Industrial": {
        "description": "Companies involved in manufacturing, logistics, and heavy industry.",
        "subcategories": {
            "Manufacturing": "Producers of industrial and consumer products.",
            "Logistics": "Supply chain management, transportation, and warehousing."
        }
    },
    "Automotive": {
        "description": "Companies that design, manufacture, and sell vehicles and auto parts.",
        "subcategories": {
            "Vehicles": "Manufacturers of cars, trucks, and motorcycles.",
            "Auto Parts": "Producers of components and accessories.",
            "Electric Vehicles": "Specialized manufacturers of electric-powered vehicles."
        }
    }
}

PRODUCT_TEMPLATES = {
    "Technology": {
        "Smartphone": {
            "requires_randd": True,
            "base_quality": 10,
            "stats": {
                "base_performance": 10,
                "base_battery_life": 10,
                "base_graphics": 10,
                "base_design": 10,
                "base_usability": 10,
                "base_marketability": 10
            },
            "base_production": 100,
            "base_manufacture_cost": 50,
            "prod_to_cust_ratio": 1.0,
            "accessories_included": False
        }
    }
}