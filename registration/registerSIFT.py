import cv2
import numpy as np
from datetime import datetime

def _find_homography_from_descriptors(target, kp2, des2, source, kp1, des1, keep_match=0.75, mode="homography", verbose=False, convertto256=True, method="SIFT"):
    if verbose: print(datetime.now().strftime("%H:%M:%S"),"- Match descriptors")
    matcher = cv2.BFMatcher(cv2.NORM_L1, crossCheck = False)
    matches = matcher.knnMatch(des1, des2, k = 2)
    
    good_matches = []
    for m,n in matches:
        if m.distance < keep_match * n.distance:
            good_matches.append([m])
    
    if verbose: print(datetime.now().strftime("%H:%M:%S"),"- Found",len(good_matches),"good matches.")
    
    if verbose: print(datetime.now().strftime("%H:%M:%S"),"- Find Homography")
    ref_matched_kpts = np.float32([kp1[m[0].queryIdx].pt for m in good_matches])
    sensed_matched_kpts = np.float32([kp2[m[0].trainIdx].pt for m in good_matches])
    
    if mode=="homography":
        homography_toTarget, _ = cv2.findHomography(ref_matched_kpts, sensed_matched_kpts, cv2.RANSAC)
        # Invert to use them interchangeably
        #homography_toRes, _ = cv2.findHomography(ref_matched_kpts, sensed_matched_kpts, cv2.RANSAC)
        homography_fromTarget = np.linalg.inv(homography_toTarget)
        homography_fromTarget = homography_fromTarget/homography_fromTarget[2,2]
        return homography_toTarget, homography_fromTarget
    
    elif mode=="partialaffine":
        homography_toTarget, _  = cv2.estimateAffinePartial2D(ref_matched_kpts, sensed_matched_kpts, method = cv2.RANSAC, ransacReprojThreshold = 5)
        homography_fromTarget, _  = cv2.estimateAffinePartial2D(sensed_matched_kpts, ref_matched_kpts, method = cv2.RANSAC, ransacReprojThreshold = 5)
        return homography_toTarget, homography_fromTarget
    elif mode=="affine":
        homography_toTarget, _  = cv2.estimateAffine2D(ref_matched_kpts, sensed_matched_kpts, method = cv2.RANSAC, ransacReprojThreshold = 5)
        homography_fromTarget, _  = cv2.estimateAffine2D(sensed_matched_kpts, ref_matched_kpts, method = cv2.RANSAC, ransacReprojThreshold = 5)
        return homography_toTarget, homography_fromTarget
    else:
        assert False

def find_homography(target, source, keep_match=0.75, mode="homography", verbose=False, convertto256=True, method="SIFT"):
    if not mode in ["homography", "partialaffine", "affine"]: raise ValueError("Unknown mode!")
    if not method in ["ORB", "SIFT"]: raise ValueError("Unknown mode!")
    if method == "ORB": raise ValueError("Don't use this, ORB sucks!")
    
    if verbose: print(datetime.now().strftime("%H:%M:%S"),"- Find Descriptors")
    
    descriptor = cv2.SIFT_create()
        
    source = (source/source.max()*255).astype('uint8')
    kp1, des1 = descriptor.detectAndCompute(source, None)
    target = (target/target.max()*255).astype('uint8')
    kp2, des2 = descriptor.detectAndCompute(target, None)
    
    return _find_homography_from_descriptors(target, kp2, des2, source, kp1, des1, keep_match, mode, verbose, convertto256, method)

def find_homographies(target, sources, keep_match=0.75, mode="homography", verbose=False, convertto256=True, method="SIFT"):
    if not mode in ["homography", "partialaffine", "affine"]: raise ValueError("Unknown mode!")
    if not method in ["ORB", "SIFT"]: raise ValueError("Unknown mode!")
    if method == "ORB": raise ValueError("Don't use this, ORB sucks!")
    
    if verbose: print(datetime.now().strftime("%H:%M:%S"),"- Find Descriptors")
    
    descriptor = cv2.SIFT_create()
    target = (target/target.max()*255).astype('uint8')
    kp2, des2 = descriptor.detectAndCompute(target, None)
    
    homographies = []
    for i, source_ in enumerate(sources):
        if verbose: print(datetime.now().strftime("%H:%M:%S"),"- Apply to source",i,"of",len(sources),".")
        source = (source_/source_.max()*255).astype('uint8')
        kp1, des1 = descriptor.detectAndCompute(source, None)
        homographies.append(_find_homography_from_descriptors(target, kp2, des2, source, kp1, des1, keep_match, mode, verbose, convertto256, method))
    
    return homographies

def warp_image(target, source, homography, mode="homography"):
    if not mode in ["homography", "partialaffine", "affine"]:
        raise ValueError("Unknown mode!")
    
    if mode=="homography":
        warped_image = cv2.warpPerspective(source, homography, (target.shape[1], target.shape[0]))
        return warped_image
    
    elif mode in ["partialaffine", "affine"]:
        warped_image = cv2.warpAffine(source, homography, (target.shape[1], target.shape[0]))
        return warped_image
        
    else:
        assert False

def transform_coordinate(homography, x, y, mode="homography"):
    if not mode in ["homography", "partialaffine", "affine"]:
        raise ValueError("Unknown mode!")
    
    xp = homography[0,0]*x + homography[0,1]*y + homography[0,2]
    yp = homography[1,0]*x + homography[1,1]*y + homography[1,2]
    
    if mode=="homography":
        sf = homography[2,0]*x + homography[2,1]*y + homography[2,2]
        return xp/sf, yp/sf
    
    elif mode in ["partialaffine", "affine"]:
        return xp, yp
        
    else:
        assert False

def scale_homography(homography, scale_target, scale_source, mode="homography"):
    """ Scale homography to target, if registration was done by downsampling
        with scale_target and scale_source.
    """
    if not mode in ["homography", "partialaffine", "affine"]:
        raise ValueError("Unknown mode!")
    
    if mode=="homography":
        return np.asarray([scale_target,scale_target,1])[:,None]*homography*np.asarray([1/scale_source,1/scale_source,1])[None,:]
    
    elif mode in ["partialaffine", "affine"]:
        return np.asarray([scale_target,scale_target])[:,None]*homography_fromA1*np.asarray([1/scale_source,1/scale_source,1])[None,:]
        
    else:
        assert False
    