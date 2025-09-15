# MLB Playoff Race Tracker

**Live App**: [https://mlb-playoff-race-tracker.onrender.com](https://mlb-playoff-race-tracker.onrender.com)

Real-time standings visualization that displays the MLB playoff race as racing lanes. Teams move from left to right, with the right side representing division clinch. Built with Python, Streamlit, Supabase, PostgreSQL, and hosted on Render.

## Features

- Racing lane visualization of division races
- Real-time standings data from MLB Stats API
- Magic number calculations for division leaders
- Team positioning based on distance from clinching
- Live updates of win-loss records and games back

## How It Works

Teams appear as circles in racing lanes. Position on the track shows how close they are to clinching their division. The green line on the right represents the division clinch line - teams that reach it have clinched their division. Eliminated teams (marked with X) are mathematically eliminated from winning their division, but may still qualify for playoffs as wild cards.

<img width="6271" height="2636" alt="_C__Users_craig_Downloads_mlb-playoff-race-tracker onrender com_(High20Res) png(High Res) (2)" src="https://github.com/user-attachments/assets/dba2fc2e-fad2-4cb9-8b63-77db8597429b" />

<img width="3078" height="178" alt="image" src="https://github.com/user-attachments/assets/949218c7-f280-424d-93e9-060ab1fc9a0e" />

## Tech Stack

- **Backend**: Python
- **Frontend**: Streamlit
- **Database**: Supabase (PostgreSQL)
- **Hosting**: Render
- **Data Source**: MLB Stats API

## Data Processing
- Fetches team and standings data from MLB Stats API using multi-threaded calls
- Calculates magic numbers using traditional baseball formulas, validated against official sources
- Determines playoff seeding with proper tiebreaker logic (win percentage, then league rank)
- Team positioning based on distance from clinch calculations
- Batch upsert operations to database with error handling
- Updates all 30 MLB teams across 6 divisions in real-time
