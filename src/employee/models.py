import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from phonenumber_field.modelfields import PhoneNumberField

from employee.utility import code_format
from employee.managers import EmployeeManager
from leave.models import Leave


# ---------------------------------------------------------
# RELIGION MODEL
# ---------------------------------------------------------
class Religion(models.Model):
    name = models.CharField(max_length=125)
    description = models.CharField(max_length=125, null=True, blank=True)

    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), auto_now=True)

    class Meta:
        verbose_name = _('Religion')
        verbose_name_plural = _('Religions')
        ordering = ['name', 'created']

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# NATIONALITY MODEL
# ---------------------------------------------------------
class Nationality(models.Model):
    name = models.CharField(max_length=125)
    description = models.CharField(max_length=125, null=True, blank=True)

    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), auto_now=True)

    class Meta:
        verbose_name = _('Nationality')
        verbose_name_plural = _('Nationalities')
        ordering = ['name', 'created']

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# ROLE MODEL
# ---------------------------------------------------------
class Role(models.Model):
    name = models.CharField(max_length=125)
    description = models.CharField(max_length=125, null=True, blank=True)

    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), auto_now=True)

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        ordering = ['name', 'created']

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# DEPARTMENT MODEL
# ---------------------------------------------------------
class Department(models.Model):
    name = models.CharField(max_length=125)
    description = models.CharField(max_length=125, null=True, blank=True)

    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), auto_now=True)

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name', 'created']

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# EMPLOYEE MODEL
# ---------------------------------------------------------
class Employee(models.Model):

    # -----------------------
    # Gender Choices
    # -----------------------
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'
    NOT_KNOWN = 'Not Known'

    GENDER = (
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        (OTHER, 'Other'),
        (NOT_KNOWN, 'Not Known'),
    )

    # -----------------------
    # Title Choices
    # -----------------------
    MR = 'Mr'
    MRS = 'Mrs'
    MSS = 'Mss'
    DR = 'Dr'
    SIR = 'Sir'
    MADAM = 'Madam'

    TITLE = (
        (MR, 'Mr'),
        (MRS, 'Mrs'),
        (MSS, 'Mss'),
        (DR, 'Dr'),
        (SIR, 'Sir'),
        (MADAM, 'Madam'),
    )

    # -----------------------
    # Employee Type Choices
    # -----------------------
    FULL_TIME = 'Full-Time'
    PART_TIME = 'Part-Time'
    CONTRACT = 'Contract'
    INTERN = 'Intern'

    EMPLOYEETYPE = (
        (FULL_TIME, 'Full-Time'),
        (PART_TIME, 'Part-Time'),
        (CONTRACT, 'Contract'),
        (INTERN, 'Intern'),
    )

    # -----------------------
    # Personal Data
    # -----------------------
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

    image = models.FileField(
        _('Profile Image'),
        upload_to='profiles',
        default='default.png',
        blank=True,
        null=True,
        help_text='Upload image size less than 2MB'
    )

    firstname = models.CharField(_('Firstname'), max_length=125)
    lastname = models.CharField(_('Lastname'), max_length=125)
    othername = models.CharField(_('Othername (optional)'), max_length=125, null=True, blank=True)

    birthday = models.DateField(_('Birthday'))

    # New fields for religion and nationality
    religion = models.ForeignKey(Religion, verbose_name=_('Religion'),
                                 on_delete=models.SET_NULL, null=True, blank=True)
    nationality = models.ForeignKey(Nationality, verbose_name=_('Nationality'),
                                    on_delete=models.SET_NULL, null=True, blank=True)

    department = models.ForeignKey(Department, verbose_name=_('Department'),
                                   on_delete=models.SET_NULL, null=True)
    role = models.ForeignKey(Role, verbose_name=_('Role'),
                             on_delete=models.SET_NULL, null=True)

    startdate = models.DateField(_('Employment Date'), null=True)
    employeetype = models.CharField(_('Employee Type'), max_length=15,
                                    choices=EMPLOYEETYPE, default=FULL_TIME, null=True)

    employeeid = models.CharField(_('Employee ID Number'), max_length=10, null=True, blank=True)
    dateissued = models.DateField(_('Date Issued'), null=True)

    # -------- App Flags ---------
    is_blocked = models.BooleanField(_('Is Blocked'), default=False)
    is_deleted = models.BooleanField(_('Is Deleted'), default=False)

    created = models.DateTimeField(_('Created'), auto_now_add=True, null=True)
    updated = models.DateTimeField(_('Updated'), auto_now=True, null=True)

    # Custom Manager
    objects = EmployeeManager()

    class Meta:
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        ordering = ['-created']

    def __str__(self):
        return self.get_full_name or "Unnamed Employee"

    # -----------------------------------------------------
    # GET FULL NAME
    # -----------------------------------------------------
    @property
    def get_full_name(self):
        firstname = self.firstname or ""
        lastname = self.lastname or ""
        othername = self.othername or ""

        if othername:
            return f"{firstname} {lastname} {othername}".strip()

        return f"{firstname} {lastname}".strip()

    # -----------------------------------------------------
    # GET AGE
    # -----------------------------------------------------
    @property
    def get_age(self):
        if not self.birthday:
            return None

        today = datetime.date.today()
        age = today.year - self.birthday.year

        if (today.month, today.day) < (self.birthday.month, self.birthday.day):
            age -= 1
        return age

    # -----------------------------------------------------
    # CAN APPLY LEAVE (Future Use)
    # -----------------------------------------------------
    @property
    def can_apply_leave(self):
        """
        Placeholder for leave-logic.
        You can add logic like:
        Count leave for current year, compare with allowed days etc.
        """
        return True

    # -----------------------------------------------------
    # SAVE (override)
    # -----------------------------------------------------
    def save(self, *args, **kwargs):
        """
        Auto-formatting employee ID before saving model.
        """
        if self.employeeid:
            self.employeeid = code_format(self.employeeid)

        super().save(*args, **kwargs)
