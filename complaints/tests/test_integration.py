"""
Integration tests for the enhanced complaints system
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import (
    Complaint,
    ComplaintNotification,
    ComplaintType,
    ComplaintUpdate,
    Department,
)
from ..services.notification_service import notification_service

User = get_user_model()


class ComplaintsSystemIntegrationTest(TestCase):
    """
    Comprehensive integration tests for the complaints system
    """

    def setUp(self):
        """Set up test data"""
        # Clear cache
        cache.clear()

        # Create users
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        self.manager_user = User.objects.create_user(
            username="manager", email="manager@test.com", password="testpass123"
        )

        self.employee_user = User.objects.create_user(
            username="employee", email="employee@test.com", password="testpass123"
        )

        # Create department
        self.department = Department.objects.create(
            name="خدمة العملاء", manager=self.manager_user
        )

        # Create complaint type
        self.complaint_type = ComplaintType.objects.create(
            name="شكوى فنية", description="شكاوى متعلقة بالمسائل الفنية"
        )

        # Create customer (assuming Customer model exists)
        try:
            from customers.models import Customer

            self.customer = Customer.objects.create(
                name="عميل تجريبي", email="customer@test.com", phone="123456789"
            )
        except ImportError:
            # If Customer model doesn't exist, create a mock
            self.customer = type(
                "Customer",
                (),
                {"id": 1, "name": "عميل تجريبي", "email": "customer@test.com"},
            )()

        # Create test complaint
        self.complaint = Complaint.objects.create(
            title="شكوى تجريبية",
            description="وصف الشكوى التجريبية",
            customer=self.customer,
            complaint_type=self.complaint_type,
            assigned_department=self.department,
            assigned_to=self.employee_user,
            created_by=self.admin_user,
            status="new",
            priority="medium",
        )

        self.client = Client()

    def test_dashboard_performance_optimization(self):
        """Test dashboard performance optimizations"""
        self.client.login(username="admin", password="testpass123")

        # First request - should cache results
        response = self.client.get(reverse("complaints:dashboard"))
        self.assertEqual(response.status_code, 200)

        # Check that cache is used
        cache_key = f"complaints_dashboard_stats_{self.admin_user.id}"
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)

        # Second request - should use cache
        response = self.client.get(reverse("complaints:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_notification_service_integration(self):
        """Test notification service integration"""
        # Test new complaint notification
        with patch(
            "complaints.services.notification_service.send_mail"
        ) as mock_send_mail:
            notification_service.notify_new_complaint(self.complaint)

            # Check that notification was created
            notifications = ComplaintNotification.objects.filter(
                complaint=self.complaint, notification_type="new_complaint"
            )
            self.assertTrue(notifications.exists())

            # Check that email was sent to assigned user
            self.assertTrue(mock_send_mail.called)

    def test_status_update_api(self):
        """Test status update API endpoint"""
        self.client.login(username="employee", password="testpass123")

        url = reverse(
            "complaints:api_status_update", kwargs={"complaint_id": self.complaint.id}
        )
        data = {"status": "in_progress"}

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that complaint status was updated
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, "in_progress")

        # Check that update record was created
        updates = ComplaintUpdate.objects.filter(
            complaint=self.complaint, update_type="status_change"
        )
        self.assertTrue(updates.exists())

    def test_assignment_update_api(self):
        """Test assignment update API endpoint"""
        self.client.login(username="manager", password="testpass123")

        url = reverse(
            "complaints:api_assignment_update",
            kwargs={"complaint_id": self.complaint.id},
        )
        data = {"assigned_to": self.manager_user.id}

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Check that complaint assignment was updated
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.assigned_to, self.manager_user)

    def test_search_api(self):
        """Test search API endpoint"""
        self.client.login(username="admin", password="testpass123")

        url = reverse("complaints:api_search")
        response = self.client.get(url, {"q": "تجريبية"})

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertEqual(len(response_data["results"]), 1)
        self.assertEqual(response_data["results"][0]["id"], self.complaint.id)

    def test_stats_api(self):
        """Test statistics API endpoint"""
        self.client.login(username="admin", password="testpass123")

        url = reverse("complaints:api_stats")
        response = self.client.get(url, {"days": 30})

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertIn("stats", response_data)
        self.assertEqual(response_data["stats"]["total"], 1)

    def test_notifications_api(self):
        """Test notifications API endpoint"""
        # Create a notification
        ComplaintNotification.create_notification(
            complaint=self.complaint,
            notification_type="new_complaint",
            recipient=self.employee_user,
            title="إشعار تجريبي",
            message="رسالة تجريبية",
        )

        self.client.login(username="employee", password="testpass123")

        url = reverse("complaints:api_notifications")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])
        self.assertEqual(len(response_data["notifications"]), 1)
        self.assertEqual(response_data["unread_count"], 1)

    def test_cross_module_integration(self):
        """Test cross-module integration features"""
        self.client.login(username="admin", password="testpass123")

        # Test complaint detail page with cross-module navigation
        response = self.client.get(
            reverse("complaints:complaint_detail", kwargs={"pk": self.complaint.id})
        )
        self.assertEqual(response.status_code, 200)

        # Check that customer information is accessible
        self.assertContains(response, self.customer.name)

    def test_template_tags_functionality(self):
        """Test custom template tags"""
        from ..templatetags.complaints_tags import (
            complaint_priority_badge,
            complaint_status_badge,
            get_complaint_stats_for_period,
        )

        # Test status badge
        badge_html = complaint_status_badge("new")
        self.assertIn("badge", badge_html)
        self.assertIn("جديدة", badge_html)

        # Test priority badge
        priority_html = complaint_priority_badge("high")
        self.assertIn("badge", priority_html)
        self.assertIn("عالية", priority_html)

        # Test stats function
        stats = get_complaint_stats_for_period(30)
        self.assertIn("total", stats)
        self.assertEqual(stats["total"], 1)

    def test_database_optimization_command(self):
        """Test database optimization management command"""
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("optimize_complaints_db", "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("CREATE INDEX", output)
        self.assertIn("dry-run", output.lower())

    def test_form_validation_enhancements(self):
        """Test enhanced form validation"""
        from ..forms import ComplaintForm

        # Test valid form
        form_data = {
            "title": "شكوى جديدة",
            "description": "وصف الشكوى",
            "customer": self.customer.id,
            "complaint_type": self.complaint_type.id,
            "priority": "medium",
        }

        form = ComplaintForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Test invalid form
        invalid_data = {
            "title": "",  # Required field
            "description": "وصف",
            "customer": self.customer.id,
            "complaint_type": self.complaint_type.id,
            "priority": "invalid_priority",
        }

        form = ComplaintForm(data=invalid_data)
        self.assertFalse(form.is_valid())

    def test_ui_enhancements(self):
        """Test UI enhancements in templates"""
        self.client.login(username="admin", password="testpass123")

        # Test dashboard UI
        response = self.client.get(reverse("complaints:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "floating-action-btn")
        self.assertContains(response, "dashboard-card")

        # Test complaint list UI
        response = self.client.get(reverse("complaints:complaint_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "complaint-card")

    def test_permission_system(self):
        """Test permission system for API endpoints"""
        # Test unauthorized access
        self.client.login(username="employee", password="testpass123")

        # Employee shouldn't be able to assign complaints
        url = reverse(
            "complaints:api_assignment_update",
            kwargs={"complaint_id": self.complaint.id},
        )
        data = {"assigned_to": self.manager_user.id}

        response = self.client.post(
            url, data=json.dumps(data), content_type="application/json"
        )

        self.assertEqual(response.status_code, 403)

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
        mail.outbox.clear()
