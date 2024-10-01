import cv2
import time
import threading
from PIL import Image
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from torch.utils.data import DataLoader
from torchvision import datasets
import os

class Facenet:
    def __init__(self, image_folder=None, pretrained='vggface2'):
        self.image_folder = image_folder
        self.pretrained = pretrained

        # Initialize MTCNN and InceptionResnetV1
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        print('Running on device: {}'.format(self.device))

        self.mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20,
                           thresholds=[0.6, 0.7, 0.7], factor=0.709, post_process=True, keep_all=True,
                           device=self.device)

        self.resnet = InceptionResnetV1(pretrained=self.pretrained).eval().to(self.device)

        if self.image_folder:
            # Load dataset
            dataset = datasets.ImageFolder(self.image_folder)
            loader = DataLoader(dataset, collate_fn=lambda x: x[0])

            # Preprocess images and extract embeddings
            aligned = []
            self.names = []
            
            for idx, (img, _) in enumerate(loader):
                img_aligned, prob = self.mtcnn(img, return_prob=True)
                if img_aligned is not None:
                    img_aligned = img_aligned[0]  # Remove any extra dimension (the second dimension)
                    aligned.append(img_aligned)
                    
                    # Get relative image path in form {user_folder}/{img_file}
                    image_path = dataset.samples[idx][0]  # Access the correct image path using idx
                    relative_image_path = os.path.relpath(image_path, self.image_folder).replace("\\", "/")  # Ensure proper path format
                    self.names.append(relative_image_path)

            # Stack aligned images and compute embeddings
            aligned = torch.stack(aligned).to(self.device)
            embeddings = self.resnet(aligned).detach().to('cpu')

            # Convert to NumPy array
            self.embeddings_np = embeddings.numpy()

    def find(self, frame_rgb, threshold=0.6):
        frame_pil = Image.fromarray(frame_rgb)
        
        # Sử dụng MTCNN để phát hiện khuôn mặt
        frames_aligned, frames_prob = self.mtcnn(frame_pil, return_prob=True)
        
        # Kiểm tra số lượng khuôn mặt
        if frames_aligned is not None and len(self.names) > 0:
            num_faces = len(frames_aligned)

            # In ra số lượng khuôn mặt
            # print(f"Số khuôn mặt phát hiện được: {num_faces}")
        
            matches = []

            # Lặp qua từng khuôn mặt đã căn chỉnh trong khung hình
            for frame_aligned in frames_aligned:
                # Tính embedding cho từng khuôn mặt
                frame_aligned = frame_aligned.unsqueeze(0).to(self.device)
                frame_embedding = self.resnet(frame_aligned).detach().to('cpu').numpy()
                
                # Tính khoảng cách giữa embedding của khuôn mặt hiện tại và embedding trong cơ sở dữ liệu
                frame_dists = np.linalg.norm(self.embeddings_np - frame_embedding, axis=1)
                
                # Lưu trữ kết quả có khoảng cách nhỏ nhất và dưới ngưỡng
                min_dist = float('inf')
                best_match = None
                for i, dist in enumerate(frame_dists):
                    if dist < min_dist and dist < threshold:
                        min_dist = dist
                        best_match = (self.names[i], dist)

                # Thêm khuôn mặt phù hợp nhất vào kết quả nếu tìm thấy
                if best_match is not None:
                    matches.append(best_match)

            return matches

        return []

    
    # New function to compare two images
    def verify(self, frame1, frame2, threshold=0.6):
        # Convert both frames to PIL images and align faces
        frame1_pil = Image.fromarray(frame1)
        frame2_pil = Image.fromarray(frame2)

        # Get aligned faces and probabilities from both frames
        frame1_aligned, _ = self.mtcnn(frame1_pil, return_prob=True)
        frame2_aligned, _ = self.mtcnn(frame2_pil, return_prob=True)

        frame1_aligned = frame1_aligned[0]
        frame2_aligned = frame2_aligned[0]

        if frame1_aligned is not None and frame2_aligned is not None:
            # Compute embeddings for both faces
            frame1_aligned = frame1_aligned.unsqueeze(0).to(self.device)
            frame2_aligned = frame2_aligned.unsqueeze(0).to(self.device)

            frame1_embedding = self.resnet(frame1_aligned).detach().to('cpu').numpy()
            frame2_embedding = self.resnet(frame2_aligned).detach().to('cpu').numpy()

            # Compute the distance between the embeddings of the two faces
            dist = np.linalg.norm(frame1_embedding - frame2_embedding)
            print(f"Distance: ",dist)

            # Return whether the distance is below the threshold
            return dist < threshold
        
        # If face alignment failed for one or both images
        return False
    


    def update_embedding(self, new_folder=None):
        # Use the new folder if provided, otherwise use the default image folder
        folder_to_use = new_folder if new_folder else self.image_folder
        
        if not os.path.exists(folder_to_use):
            print(f"Folder {folder_to_use} does not exist.")
            return
        
        # Scan the image folder to get the current images
        current_images = []
        for user_folder in os.listdir(folder_to_use):
            user_path = os.path.join(folder_to_use, user_folder)
            if os.path.isdir(user_path):
                for img_file in os.listdir(user_path):
                    current_images.append(f"{user_folder}/{img_file}")
        
        # Convert current images list to a set for comparison
        current_images_set = set(current_images)
        
        # Images that are already embedded
        embedded_images_set = set(self.names)

        # Find the images to add (new ones)
        new_images = current_images_set - embedded_images_set
        
        # Find the images to remove (deleted ones)
        removed_images = embedded_images_set - current_images_set

        # Remove embeddings of deleted images
        if removed_images:
            removed_indices = [self.names.index(img) for img in removed_images]
            self.embeddings_np = np.delete(self.embeddings_np, removed_indices, axis=0)
            self.names = [img for img in self.names if img not in removed_images]
        
        # Print removed images
        if removed_images:
            print(f"Images removed: {list(removed_images)}")
        else:
            print("No images removed.")

        # Process new images and add them to embeddings
        if new_images:
            aligned = []
            for img_path in new_images:
                user_folder, img_file = img_path.split('/')
                img = Image.open(os.path.join(folder_to_use, user_folder, img_file))
                img_aligned, prob = self.mtcnn(img, return_prob=True)
                img_aligned = img_aligned[0]
                if img_aligned is not None:
                    aligned.append(img_aligned)
                    self.names.append(img_path)

            # Compute embeddings for new images and update
            if aligned:
                aligned = torch.stack(aligned).to(self.device)
                embeddings = self.resnet(aligned).detach().to('cpu')
                new_embeddings_np = np.array([e.numpy() for e in embeddings])
                self.embeddings_np = np.concatenate((self.embeddings_np, new_embeddings_np), axis=0)

            # Print new images added
            print(f"Images added: {list(new_images)}")
        else:
            print("No new images added.")

        print("Updated embeddings. Current number of images:", len(self.names))


    
    





    