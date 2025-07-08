from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Department, UserRole, Role

User = get_user_model()

@receiver(post_save, sender=User)
def assign_default_departments(sender, instance, created, **kwargs):
    """
    Assign default departments to new users
    """
    if created:
        # Use transaction.on_commit to delay database operations
        from django.db import transaction
        
        def assign_departments():
            try:
                # Get the default departments
                default_departments = Department.objects.filter(
                    Q(code='customers') | Q(code='orders')
                )
                
                # Assign departments to user
                for dept in default_departments:
                    instance.departments.add(dept)
                    
                print(f"Default departments assigned to user {instance.username}")
            except Exception as e:
                print(f"Error assigning default departments: {e}")
        
        transaction.on_commit(assign_departments)