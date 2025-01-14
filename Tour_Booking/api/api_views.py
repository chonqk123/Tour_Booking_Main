from .serializers import UserSerializer, TourSerializer, ChangeUserInfoSerializer
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from tour_booking.models import Tour, FavoriteTour
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import update_session_auth_hash

@api_view(["POST"])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    try:
        user = User.objects.get(username=username, is_active=True)
    except User.DoesNotExist:
        return Response({"message": _("Account does not exist")}, status=status.HTTP_401_UNAUTHORIZED)

    if user.check_password(password):
        serializer = UserSerializer(user)
        login(request, user)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        return Response({"user": serializer.data, "access_token": access_token, "message": _("Login successful"), "status": status.HTTP_200_OK})
    else:
        return Response({"message": _("Incorrect username or password")}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def toggle_favorite_tour(request, tour_id):
    tour = get_object_or_404(Tour, pk=tour_id)
    favorite, created = FavoriteTour.objects.get_or_create(user=request.user, tour=tour)

    if not created:
        favorite.delete()

    return Response({"message": "Tour đã được thêm vào danh sách yêu thích." if created else "Tour đã được xóa khỏi danh sách yêu thích."})

class FavoriteToursListView(generics.GenericAPIView):
    serializer_class = TourSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = self.request.user
        favorite_tours = FavoriteTour.objects.filter(user=user).order_by('-created_at')
        favorite_tours_list = list(favorite_tours)

        if not favorite_tours_list:
            message = "Không có tour yêu thích nào."
        else:
            message = "Danh sách các tour yêu thích."

        return Response({"message": message, "favorite_tours": TourSerializer(favorite_tours_list, many=True).data})

class ChangeUserInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        serializer = ChangeUserInfoSerializer(data=request.data, context={'user': user})
        
        if serializer.is_valid():
            new_username = serializer.validated_data.get('username', user.username)
            if new_username != user.username and User.objects.filter(username=new_username).exists():
                return Response({'message': 'Username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)
            
            old_password = serializer.validated_data['old_password']
            if not user.check_password(old_password):
                return Response({'message': 'Incorrect old password.'}, status=status.HTTP_400_BAD_REQUEST)
            
            new_password1 = serializer.validated_data['new_password1']
            new_password2 = serializer.validated_data['new_password2']
            if new_password1 != new_password2:
                return Response({'message': 'New passwords must match.'}, status=status.HTTP_400_BAD_REQUEST)
            
            new_first_name = serializer.validated_data.get('first_name', user.first_name)
            new_last_name = serializer.validated_data.get('last_name', user.last_name)
            new_email = serializer.validated_data.get('email', user.email)
            
            user.username = new_username
            user.first_name = new_first_name
            user.last_name = new_last_name
            user.email = new_email
            user.set_password(new_password1)
            user.save()
            
            updated_user_serializer = UserSerializer(user)
            return Response(updated_user_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
