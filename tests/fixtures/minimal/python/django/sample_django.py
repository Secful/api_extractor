"""Sample Django REST Framework application for testing."""

from rest_framework import viewsets, serializers
from rest_framework.decorators import api_view, action
from rest_framework.views import APIView
from rest_framework.response import Response


class UserSerializer(serializers.Serializer):
    """User serializer."""

    id = serializers.IntegerField()
    username = serializers.CharField(max_length=100)
    email = serializers.EmailField()


class ItemSerializer(serializers.Serializer):
    """Item serializer."""

    id = serializers.IntegerField()
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)


class UserViewSet(viewsets.ModelViewSet):
    """User ViewSet with CRUD operations."""

    serializer_class = UserSerializer

    def list(self, request):
        """List all users."""
        return Response([])

    def retrieve(self, request, pk=None):
        """Retrieve a single user."""
        return Response({"id": pk})

    def create(self, request):
        """Create a new user."""
        return Response({})

    def update(self, request, pk=None):
        """Update a user."""
        return Response({"id": pk})

    def destroy(self, request, pk=None):
        """Delete a user."""
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        """Custom action to set password."""
        return Response({"status": "password set"})


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    """Item ViewSet with read-only operations."""

    serializer_class = ItemSerializer

    def list(self, request):
        """List all items."""
        return Response([])

    def retrieve(self, request, pk=None):
        """Retrieve a single item."""
        return Response({"id": pk})


class ProductAPIView(APIView):
    """Product API view."""

    def get(self, request):
        """List products."""
        return Response([])

    def post(self, request):
        """Create product."""
        return Response({})


@api_view(["GET", "POST"])
def order_list(request):
    """Order list endpoint."""
    if request.method == "GET":
        return Response([])
    else:
        return Response({})


@api_view(["GET"])
def health_check(request):
    """Health check endpoint."""
    return Response({"status": "ok"})
