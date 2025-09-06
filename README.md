# eAuction - Django Auction Platform

A Django-based auction platform with admin and public panels.

## Features

- User authentication and authorization
- Product management with auction functionality
- Bidding system
- Admin panel for managing products, users, and auctions
- Public panel for users to browse and bid on products
- Responsive design with Bootstrap

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd project
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Access URLs

- **Main Site**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/arjun/
- **Django Admin**: http://127.0.0.1:8000/admin/

## Default Admin Credentials

- **Username**: admin
- **Password**: admin123

## Project Structure

- `App/` - Main application with models and core functionality
- `admin_panel/` - Admin panel views and templates
- `public_panel/` - Public user interface
- `templates/` - HTML templates
- `static/` - Static files (CSS, JS, images)
- `media/` - User uploaded files

## Models

- **User** - Custom user model with admin/user types
- **Product** - Products available for auction
- **Bidnow** - Bidding records
- **Customer** - Customer information
- **AboutUs** - About us content
- **ContactUs** - Contact form submissions
- **SiteSetting** - Site configuration
- **Feedback** - User feedback
- **AuctionWinner** - Auction results

## Features

- User registration and login
- Product browsing and searching
- Real-time bidding
- Admin dashboard with statistics
- Product management
- User management
- Auction management

## Requirements

- Python 3.8+
- Django 5.0.2
- Pillow (for image handling)
- Django Crispy Forms
- Bootstrap 4

## Development

The project is now fully functional and ready for development. All major errors have been resolved:

✅ Django installation and dependencies
✅ Model syntax errors fixed
✅ Missing apps added to settings
✅ Admin configuration completed
✅ Database migrations applied
✅ Development server running

## Troubleshooting

If you encounter any issues:

1. Make sure all dependencies are installed: `pip install -r requirements.txt`
2. Check for migration issues: `python manage.py check`
3. Verify the database: `python manage.py migrate`
4. Check the logs in `debug.log`

## License

This project is open source and available under the MIT License. 