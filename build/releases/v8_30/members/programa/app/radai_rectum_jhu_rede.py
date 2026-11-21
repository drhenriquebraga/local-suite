# -*- coding: utf-8 -*-
"""Arquiteturas de inferência da JHU/MICA, sob MIT (data/LICENCA-JHU-MICA.txt).

Fonte: JHU-MICA/TwoStepMalePelvicCTSeg, commit c0e7b3d593ca45db39c1b6d1a3f824a14aa24874,
coarse_to_fine/{models,backbones/blocks,transformer/{net,axial_transformer}}.py.
Apenas as arquiteturas utilizadas pelos checkpoints de localização, reto e próstata.
"""
from typing import Sequence, Tuple, Union
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import monai.networks.blocks as mn


class qkv_transform(nn.Conv1d):
    """Conv1d for qkv_transform"""

class RelativeAxialAttention(nn.Module):

    def __init__(
        self,
        img_shape,
        in_channels,
        num_heads = 8,
        dk = 8,
        dv = 16,
        axial_dim = 0,
        cross_attention = False,
        q_channels = None,
        gated = True
        ):

        ''' 
        3D Axial Attention 
        in_channels: input channels
        img_shape: size of input
        num_heads: number of attention heads
        dk: q/k embedding dimension
        dv: v embedding dimension
        axial_dimension: dimension to compute attention over
        gated: whether or not to use gated attention
        '''

        super(RelativeAxialAttention, self).__init__()
        self.in_planes = in_channels
        self.out_planes = num_heads * dv
        self.num_heads = num_heads
        self.dk = dk
        self.dv = dv
        self.kernel_size = img_shape[axial_dim]
        self.axial_dimension = axial_dim

        self.cross_attention = cross_attention
        self.q_channels = q_channels if q_channels is not None else in_channels
        self.gated = gated

        # Multi-head self attention
        self.kv_transform = qkv_transform(in_channels, num_heads * (dv + dk), kernel_size=1, stride=1, padding=0, bias=False)
        self.q_transform = qkv_transform(self.q_channels, num_heads * dk, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn_kv = nn.BatchNorm1d(num_heads * (dv + dk))
        self.bn_q = nn.BatchNorm1d(num_heads * dk)
        self.bn_similarity = nn.BatchNorm2d(num_heads * 3)
        self.bn_output = nn.BatchNorm1d(num_heads * dv * 2)

        # Position embedding
        self.relative = nn.Parameter(torch.randn(dv + 2 * dk, self.kernel_size * 2 - 1), requires_grad=True)
        query_index = torch.arange(self.kernel_size).unsqueeze(0)
        key_index = torch.arange(self.kernel_size).unsqueeze(1)
        relative_index = key_index - query_index + self.kernel_size - 1
        self.register_buffer('flatten_index', relative_index.view(-1))

        # Gates
        self.f_qr = nn.Parameter(torch.tensor(0.1)) 
        self.f_kr = nn.Parameter(torch.tensor(0.1))
        self.f_sve = nn.Parameter(torch.tensor(0.1))
        self.f_sv = nn.Parameter(torch.tensor(1.0))


    def forward(self, x, y = None):
        # x: input of shape N C H W D
        # y: optional input of shape N C H W D (for cross attention)

        # Convert to # N {other dims} C {needed dim}
        if self.axial_dimension == 0:
            x = x.permute(0, 3, 4, 1, 2)

        elif self.axial_dimension == 1:
            x = x.permute(0, 2, 4, 1, 3)

        else:
            x = x.permute(0, 2, 3, 1, 4)

        if self.cross_attention:
            if self.axial_dimension == 0:
                y = y.permute(0, 3, 4, 1, 2)

            elif self.axial_dimension == 1:
                y = y.permute(0, 2, 4, 1, 3)

            else:
                y = y.permute(0, 2, 3, 1, 4)

            N, W, D, C, H = y.shape
            y = y.contiguous().view(N * W * D, C, H)
            

        N, W, D, C, H = x.shape
        x = x.contiguous().view(N * W * D, C, H)


        # Transformations: q,k,v N*W*D, HEADS, D_k/D_v, H
        kv = self.bn_kv(self.kv_transform(x))
        k, v = torch.split(kv.reshape(N * W * D, self.num_heads, self.dk + self.dv, H), [self.dk, self.dv], dim=2)

        if self.cross_attention:
            q = self.bn_q(self.q_transform(y)).reshape(N * W * D, self.num_heads, self.dk, H)
        
        else:
            q = self.bn_q(self.q_transform(x)).reshape(N * W * D, self.num_heads, self.dk, H)

        # Calculate position embedding
        all_embeddings = torch.index_select(self.relative, 1, self.flatten_index).view(self.dv + 2 * self.dk, self.kernel_size, self.kernel_size)
        q_embedding, k_embedding, v_embedding = torch.split(all_embeddings, [self.dk, self.dk, self.dv], dim=0)

        qr = torch.einsum('bgci,cij->bgij', q, q_embedding)
        kr = torch.einsum('bgci,cij->bgij', k, k_embedding).transpose(2, 3)
        qk = torch.einsum('bgci, bgcj->bgij', q, k)

        if self.gated:
            qr = torch.mul(qr, self.f_qr)
            kr = torch.mul(kr, self.f_kr)

        stacked_similarity = torch.cat([qk, qr, kr], dim=1)
        stacked_similarity = self.bn_similarity(stacked_similarity).view(N * W * D, 3, self.num_heads, H, H).sum(dim=1)

        similarity = F.softmax(stacked_similarity, dim=3)
        sv = torch.einsum('bgij,bgcj->bgci', similarity, v)
        sve = torch.einsum('bgij,cij->bgci', similarity, v_embedding)

        if self.gated:
            sv = torch.mul(sv, self.f_sv)
            sve = torch.mul(sve, self.f_sve)

        stacked_output = torch.cat([sv, sve], dim=-1).view(N * W * D, self.out_planes * 2, H)
        output = self.bn_output(stacked_output).view(N, W, D, self.out_planes, 2, H).sum(dim=-2)

        if self.axial_dimension == 0:
            output = output.permute(0, 3, 4, 1, 2)

        elif self.axial_dimension == 1:
            output = output.permute(0, 3, 1, 4, 2)

        else:
            output = output.permute(0, 3, 1, 2, 4)

        return output

class AxialTransformer(nn.Module):

    def __init__(self,img_shape,in_channels,cross_channels,bn_channels=64,num_heads=8,dk=8,dv=16,dropout_rate=0.2,gated=False,**kwargs):

        '''
        transformer containing axial cross attention with relative axial position encoding
        input -> 1x1x1 conv -> x,y,z sequential axial attention -> 1x1x1 conv residual layer
        img_shape: shape of input image
        in_channels: input channels into layer
        cross_channels: channels of cross attention input
        bn_channels: bottleneck channels-> into transformer
        num_heads: number of heads for MHA
        dk: dimension of k and q per head
        dv: dimension of v per head
        dropout_rate: dropout to add to convolutions
        gated: whether or not to use gated transformer and gated residual (multiply the whole block by a constant factor) (defaults to True now)
        '''

        super(AxialTransformer, self).__init__()

        self.img_shape = img_shape
        self.in_channnels = in_channels
        self.out_channels = kwargs.pop('out_channels',cross_channels) # specify number of output channels if wanted
        self.gated = gated

        self.x_attention = RelativeAxialAttention(img_shape,bn_channels,num_heads,dk,dv,0,True,cross_channels,gated=gated)
        self.y_attention = RelativeAxialAttention(img_shape,dv*num_heads,num_heads,dk,dv,1,True,cross_channels,gated=gated)
        self.z_attention = RelativeAxialAttention(img_shape,dv*num_heads,num_heads,dk,dv,2,True,cross_channels,gated=gated)


        self.in_conv = nn.Sequential(
            nn.Conv3d(in_channels,bn_channels,1,1),
            nn.InstanceNorm3d(bn_channels),
            nn.ReLU(),
            nn.Dropout(p=dropout_rate),
        )

        self.out_conv = nn.Sequential(
            nn.Conv3d(dv*num_heads,self.out_channels,1,1),
            nn.InstanceNorm3d(self.out_channels),
            nn.LeakyReLU(negative_slope=0.1),
            nn.Dropout(p=dropout_rate),
        )

        self.trans_gate = nn.Parameter(torch.tensor(0.5))


    def forward(self,x,y):
        
        x_out = self.in_conv(x)

        x_out = self.x_attention(x_out,y)
        x_out = self.y_attention(x_out,y)
        x_out = self.z_attention(x_out,y)
        
        x_out = self.out_conv(x_out)

        if self.gated:
            return y + torch.mul(x_out, self.trans_gate)
        
        return x_out + y


class ConvAxNet(nn.Module):

    def __init__(
        self,
        img_shape: Sequence,
        in_channels: int,
        feature_list: list,
        norm_name: Union[Tuple, str] = "instance",
        subunits: int = 1, 
        dropout: float = 0.25,
        act = ('LEAKYRELU',{"negative_slope": 0.1}),
        **kwargs,
    ) -> None:

        super(ConvAxNet, self).__init__()

        self.img_shape = np.array(img_shape)
        self.in_channels = in_channels
        self.feature_list = feature_list
        self.num_layers = len(feature_list)
        self.norm = norm_name
        self.subunits = subunits
        self.dropout = dropout
        self.act = act

        self.downsample = nn.MaxPool3d(2,2)

        self.ops = nn.ModuleList()
        
        self.ops.append(self._make_layer(img_shape,in_channels,feature_list[0],add_transformer=False))

        for i in range(1,len(feature_list)):
            in_features = feature_list[i-1]
            out_features = feature_list[i]
            input_shape = self.img_shape // (2 ** i)

            self.ops.append(self._make_layer(input_shape,in_features,out_features))
    
    def _make_layer(self,input_shape,in_features,out_features,num_heads=8,dk=8,dv=16,add_transformer=True):

        convs = nn.ModuleList(
            [mn.Convolution(3,in_features,out_features,1,3,"NDA",self.act,self.norm,self.dropout)]
        )

        for _ in range(1,self.subunits):
            convs.append(
                mn.Convolution(3,out_features,out_features,1,3,"NDA",self.act,self.norm,self.dropout)
            )

        convs = nn.Sequential(*convs)

        if add_transformer:
            trans = AxialTransformer(input_shape,in_features,out_features,out_features,num_heads,dk,dv,self.dropout)
            return nn.ModuleList([convs,trans])

        return convs

    def forward(self,x):

        # returns skip connections and bottom layers
        states = []

        x = self.ops[0](x)
        states.append(x)
        x = self.downsample(x)

        for i,(conv,trans) in enumerate(self.ops[1:]):
            
            x = trans(x,conv(x)) # run convolution then transformer

            if i < self.num_layers - 2:

                states.append(x) # add to features if not bottom layer
                x = self.downsample(x)

        return x,states


def basic_conv_block(
    in_channels,
    out_channels,
    strides = 1,
    kernel_size = 3,
    act = ('LEAKYRELU',{"negative_slope": 0.1}),
    norm = 'BATCH',
    spatial_dims = 3,
    adn_ordering = 'NDA', 
    dropout = 0., 
    dilation = 1,
    groups = 1,
    bias = True,
    is_transposed = False,
    padding = None, 
    ):
    # implements a convolutional block (just wraps the monai built-in function -> has a lot of functionality)

    return mn.Convolution(
        spatial_dims,
        in_channels,
        out_channels,
        strides = strides,
        kernel_size = kernel_size,
        act = act,
        norm = norm,
        adn_ordering = adn_ordering, 
        dropout = dropout, 
        dilation = dilation,
        groups = groups,
        bias = bias,
        is_transposed = is_transposed,
        padding = padding)

class DenseBlock(nn.Module):
    """
    Basic dense block with bottleneck layers
    """

    def __init__(
        self,
        in_channels,
        out_channels,
        subunits = 2,
        strides = 1,
        kernel_size = 3,
        act = ('LEAKYRELU',{"negative_slope": 0.1}),
        norm = 'BATCH',
        spatial_dims = 3,
        adn_ordering = 'NDA', 
        dropout = 0., 
        dilation = 1,
        groups = 1,
        bias = True,
        is_transposed = False,
        padding = None,
        bn_factor = 2 # for bottleneck: mulitied by out_channels for layers in bottleneck conv
    ) -> None:

        super().__init__()

        self.ops = nn.ModuleList()
        self.subunits = subunits 

        # add transition layer if needed
        if in_channels != out_channels:
            self.ops.append(basic_conv_block(in_channels,out_channels,strides,1,act,norm,spatial_dims,adn_ordering,dropout))
        else:
            self.ops.append(nn.Identity())

        in_channels = out_channels

        # add ops
        for _ in range(subunits):
            
            self.ops.append(nn.Sequential(
                basic_conv_block(
                    in_channels,out_channels*bn_factor,strides,1,act,norm,spatial_dims,adn_ordering,dropout),
                basic_conv_block(
                    out_channels*bn_factor,out_channels,strides,kernel_size,
                    act,norm,spatial_dims,adn_ordering,dropout,
                    dilation,groups,bias,is_transposed,padding)
            ))
            
            in_channels += out_channels

        
    def forward(self,x_in):
        
        for i,op in enumerate(self.ops):
            x = op(x_in)
            
            # concatenate feature maps
            if i == 0: # first layer is just transition
                x_in = x
            else:
                x_in = torch.cat([x_in,x],1)
        
        return x


def make_layer(in_features, out_features, block_type, norm, subunits=2, dropout=0.25, **kwargs):
    if block_type == "dense":
        return DenseBlock(in_features, out_features, subunits=subunits, norm=norm, dropout=dropout, **kwargs)
    if block_type != "conv":
        raise ValueError("Bloco JHU desconhecido: %s" % block_type)
    layers = [basic_conv_block(in_features, out_features, norm=norm, dropout=dropout, **kwargs)]
    for _ in range(1, subunits):
        layers.append(basic_conv_block(out_features, out_features, norm=norm, dropout=dropout, **kwargs))
    return nn.Sequential(*layers)


class Encoder(nn.Module):
    """
    Basic Encoder for UNet
    """

    def __init__(
        self,
        in_channels: int,
        feature_list: list,
        norm_name: Union[Tuple, str] = "instance",
        block_type: str = 'conv',
        subunits: int = 2,
        dropout: float = 0.25,
        **kwargs,
    ) -> None:

        super().__init__()

        self.downsample = nn.MaxPool3d(2,2) # downsample using max pooling
        self.num_layers = len(feature_list)

        # add first layer to encoder ops
        self.ops = nn.ModuleList([make_layer(in_channels,feature_list[0],block_type,norm_name,subunits=subunits,dropout=dropout,**kwargs)])

        # add subsequent layers
        for i in range(1,len(feature_list)):
            in_features = feature_list[i-1]
            out_features = feature_list[i]
            self.ops.append(make_layer(in_features,out_features,block_type,norm_name,subunits=subunits,dropout=dropout,**kwargs))
        
    def forward(self,x):
        # returns skip connections and bottom layers
        states = []

        for i,op in enumerate(self.ops):
            x = op(x) # run the block

            if i < self.num_layers - 1:
                states.append(x) # add to features if not bottom layer
                x = self.downsample(x)

        return x,states


class GenericUnet(nn.Module):
    """
    Basic UNet with Different Backbone Options
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        img_size: Tuple[int, int, int],
        num_features: int = 16,
        num_layers: int = 4,
        norm_name: Union[Tuple, str] = "instance",
        encoder_block: str = 'conv',
        encoder_units: int = 2,
        dropout: float = 0.25,
        decoder_block: str = 'conv',
        decoder_units: int = 2,
        feature_list: list = None,
        **kwargs,
    ) -> None:
        """
        Args:
            in_channels: dimension of input channels.
            out_channels: dimension of output channels.
            img_size: dimension of input image.
            num_features: number of features in the first layer of the network
            num_layers: number of layers in the model
            feature_size: dimension of network feature size.
            norm_name: feature normalization type and arguments.
            encoder_block: type of block to use for encoder (ex. conv, res, dense)
            dropout: faction of the input units to drop.
            feature_list: if a list of features per layer is given -> overwrites the default pattern of num_features/num_layers
            ex. feature_list = [16,32,64,128] is equivalent to num_features = 16, num_layers = 4
        """

        super().__init__()

        if not (0 <= dropout <= 1):
            raise AssertionError("dropout should be between 0 and 1.")

        if feature_list is None:
            feature_list = [num_features * (2**i) for i in range(num_layers)]
            
        self.num_layers = len(feature_list)

        if encoder_block == 'axial':
            self.encoder = ConvAxNet(img_size,in_channels,feature_list,norm_name,encoder_units,dropout)
        else:
            self.encoder = Encoder(in_channels,feature_list,norm_name,encoder_block,encoder_units,dropout,**kwargs)

        # get upsampling transpose conv parameters
        self.upsample = nn.ModuleList()
        for i in range(len(feature_list)-1,0,-1):
            self.upsample.append(nn.ConvTranspose3d(feature_list[i],feature_list[i-1],2,2))

        # add ops to decoder layer
        self.decoder_ops = nn.ModuleList()

        for i in range(len(feature_list)-1,0,-1):
            in_features = feature_list[i-1]*2
            out_features = feature_list[i-1]
            self.decoder_ops.append(make_layer(in_features,out_features,decoder_block,norm_name,subunits=decoder_units,dropout=dropout,**kwargs))
        

        # out layer
        self.final_conv = nn.Conv3d(out_features,out_channels,1)

    def forward(self, x):
        
        x, encoder_features = self.encoder(x)

        for i,op in enumerate(self.decoder_ops):
            skip = encoder_features[self.num_layers-2-i]
            x = self.upsample[i](x)
            x = torch.cat([skip,x],axis=1)
            x = op(x)

        x = self.final_conv(x)
            
        return x
