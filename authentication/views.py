from rest_framework import (
    permissions, viewsets, views, status, authentication
)
from authentication.models import CustomUser
from authentication.permissions import IsCustomUserOwner
from authentication.serializers import (
                CustomUserSerializer, TokenSerializer,
                LoginSerializer, UserInfoSerializer
                )
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from django.core.mail import EmailMessage
from django.utils import timezone
from history.models import Category
import base64, hashlib


class CreateCustomUserView(views.APIView):
    lookup_field = 'username'
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = ()
    # def get_permissions(self):
    #     if self.request.method in permissions.SAFE_METHODS:
    #         return (permissions.AllowAny(),)
    #
    #     if self.request.method == 'POST':
    #         return (permissions.AllowAny(),)
    #
    #     return (permissions.IsAuthenticated(), IsCustomUserOwner(),)

    def post(self, request, format=None):

        request.data['email'] = request.data['email'].lower()

        request.data['username'] = request.data['email']

        if CustomUser.objects.filter(email=request.data['email']).exists():
            return Response({
                'status': 'Account Exists',
                'message': 'An account with this email already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            customuser = CustomUser.objects.create_user(**serializer.validated_data)

            token = Token.objects.get(user=customuser)

            email = EmailMessage('Successfully Created Account!',
                    'Thank you for signing up to use Hindsite! \n\nThe Hindsite Team',
                    to=[customuser.email])

            email.send()

            research = Category(title='Research', owned_by=customuser, color='#FA6E59')
            cooking = Category(title='Cooking', owned_by=customuser, color='#77F200')
            travel = Category(title='Travel', owned_by=customuser, color='#FFDB5C')
            news = Category(title='News', owned_by=customuser, color='#F8A055')
            research.save()
            cooking.save()
            travel.save()
            news.save()

            key = base64.b64encode(customuser.key.encode()).decode()
            md5 = base64.b64encode(hashlib.md5(customuser.key.encode()).digest()).decode()
            data = {'token': token.key,
                    'key': key,
                    'md5': md5,
                    'categories': customuser.category_set.all(),
                    'tracking': customuser.tracking_on}

            send = LoginSerializer(data)

            return Response(send.data)

        return Response({
            'status': 'Bad request',
            'message': 'Account could not be created with received data.'
        }, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    authentication_classes = ()
    permission_classes = ()

    def post(self, request, format=None):

        email = request.data['email'].lower()
        password = request.data['password']

        customuser = authenticate(email=email, password=password)

        if customuser is not None:
            if customuser.is_active:
                login(request, customuser)

                token = Token.objects.get(user=customuser)
                key = base64.b64encode(customuser.key.encode()).decode()
                md5 = base64.b64encode(hashlib.md5(customuser.key.encode()).digest()).decode()
                data = {'token': token.key,
                        'key': key,
                        'md5': md5,
                        'categories': customuser.category_set.all(),
                        'tracking': customuser.tracking_on}

                send = LoginSerializer(data)

                return Response(send.data)
            else:
                return Response({
                    'status': 'Unauthorized',
                    'message': 'This account has been disabled.'
                }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({
                'status': 'Unauthorized',
                'message': 'Username/password combination invalid.'
            }, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(views.APIView):

    def post(self, request, format=None):

        cu = request.user

        time = timezone.now()

        for d in cu.domain_set.filter(closed__isnull=True):
            d.closed = time
            d.save()
            d.tab.closed = time
            d.tab.save()

        ta = cu.timeactive_set.filter(end__isnull=True)

        if ta.exists():
            ta = ta.first()
            ta.end = time
            ta.save()

        logout(request)

        return Response({}, status=status.HTTP_204_NO_CONTENT)

class ForgotPassword(views.APIView):
    permission_classes = ()

    def post(self, request, format=None):

        email_send = request.data['email'].lower()

        customuser = CustomUser.objects.filter(email=email_send)

        if customuser.exists():
            customuser = customuser.first()

            new_pw = CustomUser.objects.make_random_password()

            customuser.set_password(new_pw)

            customuser.save()

            email = EmailMessage('New Password',
                    'The new password for your account is: ' + new_pw,
                    to=[email_send])

            email.send()
        return Response()

class ChangePassword(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):

        current_pw = request.data['current_pw']
        new_pw = request.data['new_pw']

        customuser = authenticate(email=request.user.email, password=current_pw)

        if customuser is not None:
            customuser.set_password(new_pw)
            customuser.save()

            email = EmailMessage('Changed Password',
                    'You have successfully changed your password! \n\n If this was not you please reply to this email.\n\nThe Hindsite Team',
                    to=[customuser.email])

            email.send()

            return Response({
                'status': 'OK',
                'message': 'Password successfully updated'
                })
        else:
            return Response({
                'status': 'Unauthorized',
                'message': 'Current password incorrect'
            }, status=status.HTTP_401_UNAUTHORIZED)

class ChangeTracking(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)
    # authentication_classes = ()

    def post(self, request, format=None):
        cu = request.user

        tracking = request.data['tracking']

        cu.tracking_on = tracking
        cu.save()

        if not tracking:
            time = timezone.now()

            for d in cu.domain_set.filter(closed__isnull=True):
                d.closed = time
                d.save()
                d.tab.closed = time
                d.tab.save()

            ta = cu.timeactive_set.filter(end__isnull=True)

            if ta.exists():
                ta = ta.first()
                ta.end = time
                ta.save()

        user = UserInfoSerializer(cu)

        return Response(user.data)

class GetDecryption(views.APIView):

    def get(self, request, format=None):
        cu = request.user

        token = Token.objects.get(user=cu)
        key = base64.b64encode(cu.key.encode()).decode()
        md5 = base64.b64encode(hashlib.md5(cu.key.encode()).digest()).decode()
        data = {'token': token.key,
                'key': key,
                'md5': md5}

        send = LoginSerializer(data)

        return Response(send.data)
