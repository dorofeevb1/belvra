from rest_framework import serializers

from apps.users.serializers import MasterProfileSerializer

from .models import Category, MasterService, PortfolioItem, Service


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    services_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image", "is_active", "services_count"]

    def get_services_count(self, obj):
        return obj.services.filter(is_active=True).count()


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for Service model."""

    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "category", "category_name", "name", "slug",
            "description", "image", "price", "duration",
            "is_active", "is_popular"
        ]


class ServiceDetailSerializer(ServiceSerializer):
    """Detailed serializer for Service with masters."""

    masters = serializers.SerializerMethodField()

    class Meta(ServiceSerializer.Meta):
        fields = ServiceSerializer.Meta.fields + ["masters"]

    def get_masters(self, obj):
        master_services = MasterService.objects.filter(
            service=obj,
            master__is_available=True
        ).select_related("master__user")
        return MasterServiceSerializer(master_services, many=True).data


class MasterServiceSerializer(serializers.ModelSerializer):
    """Serializer for MasterService."""

    master = MasterProfileSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    actual_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    actual_duration = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    is_custom = serializers.BooleanField(read_only=True)
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = MasterService
        fields = [
            "id", "master", "service", "price", "duration", "materials_cost",
            "actual_price", "actual_duration", "name", "description",
            "custom_name", "custom_description", "category", "category_name",
            "is_custom", "is_active"
        ]

    def get_category_name(self, obj):
        if obj.category:
            return obj.category.name
        if obj.service and obj.service.category:
            return obj.service.category.name
        return None


class MasterServiceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating MasterService.

    Supports two modes:
    1. Catalog service: provide service_id to link to catalog service
    2. Custom service: provide custom_name, price, duration (service_id is null)
    """

    service_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = MasterService
        fields = [
            "id", "service_id", "custom_name", "custom_description",
            "category", "price", "duration", "materials_cost", "is_active"
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        """Validate that either service_id or custom_name is provided."""
        service_id = data.get('service_id')
        custom_name = data.get('custom_name')

        # For creation, require either service_id or custom_name
        if not self.instance:  # Creating
            if not service_id and not custom_name:
                raise serializers.ValidationError(
                    "Either service_id (for catalog service) or custom_name (for custom service) is required."
                )

        return data

    def create(self, validated_data):
        service_id = validated_data.pop('service_id', None)

        if service_id:
            # Catalog service
            try:
                service = Service.objects.get(id=service_id)
                validated_data['service'] = service
            except Service.DoesNotExist:
                raise serializers.ValidationError({"service_id": "Service not found"})
        else:
            # Custom service - ensure we have required fields
            if not validated_data.get('custom_name'):
                raise serializers.ValidationError({"custom_name": "Name is required for custom services"})
            if not validated_data.get('price'):
                raise serializers.ValidationError({"price": "Price is required for custom services"})
            if not validated_data.get('duration'):
                raise serializers.ValidationError({"duration": "Duration is required for custom services"})

        return MasterService.objects.create(**validated_data)

    def update(self, instance, validated_data):
        service_id = validated_data.pop('service_id', None)

        if service_id:
            try:
                instance.service = Service.objects.get(id=service_id)
                # Clear custom fields when switching to catalog service
                instance.custom_name = ''
                instance.custom_description = ''
            except Service.DoesNotExist:
                raise serializers.ValidationError({"service_id": "Service not found"})

        # Update other fields
        instance.custom_name = validated_data.get('custom_name', instance.custom_name)
        instance.custom_description = validated_data.get('custom_description', instance.custom_description)
        instance.category = validated_data.get('category', instance.category)
        instance.price = validated_data.get('price', instance.price)
        instance.duration = validated_data.get('duration', instance.duration)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()
        return instance


class PortfolioItemSerializer(serializers.ModelSerializer):
    """Serializer for PortfolioItem."""

    master_name = serializers.CharField(source="master.user.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True, allow_null=True)

    class Meta:
        model = PortfolioItem
        fields = [
            "id", "master", "master_name", "title", "description",
            "image", "service", "service_name", "hashtags",
            "likes_count", "is_published", "is_pinned", "created_at"
        ]
        read_only_fields = ["id", "master", "likes_count", "created_at"]


class PortfolioItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating PortfolioItem."""

    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        required=False,
        allow_null=True
    )
    is_published = serializers.BooleanField(default=True)

    class Meta:
        model = PortfolioItem
        fields = ["id", "title", "description", "image", "service", "hashtags", "is_published"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not hasattr(request.user, "master_profile"):
            raise serializers.ValidationError("Только мастер может добавлять работы в портфолио")
        validated_data["master"] = request.user.master_profile
        return super().create(validated_data)
