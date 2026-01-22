export interface Review {
  id: string;
  masterId: string;
  clientId: string;
  clientName: string;
  clientAvatar?: string;
  appointmentId: string;
  rating: number;
  comment: string;
  createdAt: Date;
}

export interface ReviewStats {
  averageRating: number;
  totalReviews: number;
  ratingDistribution: {
    5: number;
    4: number;
    3: number;
    2: number;
    1: number;
  };
}
